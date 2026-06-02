"""Load module — writes transformed data to the OLAP warehouse."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import pandas as pd
from etl.lineage import LineageEvent, LineageTracker
from sqlalchemy import text
from sqlalchemy.engine import Connection

log = logging.getLogger("insightflow.load")

_SOURCE_DB = "insightflow_app"
_WAREHOUSE_DB = "insightflow_star_schema"

# Static SQL for each lookup dimension — avoids dynamic string construction.
# All identifiers are literals; no user input reaches these strings.
_LOOKUP_SQL: dict[str, dict[str, str]] = {
    "dimStore": {
        "insert": (
            'INSERT INTO "dimStore" ("storeId", "storeName", "province") '
            "VALUES (:storeId, :storeName, :province) "
            'ON CONFLICT ("storeId") DO NOTHING'
        ),
        "select": (
            'SELECT "storeId", "storeKey" FROM "dimStore" '
            'WHERE "storeId" = ANY(:names)'
        ),
    },
    "dimGeography": {
        "insert": (
            'INSERT INTO "dimGeography" ("province", "country") '
            "VALUES (:province, :country) "
            'ON CONFLICT ("province", "country") DO NOTHING'
        ),
        "select": (
            'SELECT "province", "geographyKey" FROM "dimGeography" '
            'WHERE "province" = ANY(:names)'
        ),
    },
    "dimChannel": {
        "insert": (
            'INSERT INTO "dimChannel" ("channelName", "channelType") '
            "VALUES (:channelName, :channelType) "
            'ON CONFLICT ("channelName") DO NOTHING'
        ),
        "select": (
            'SELECT "channelName", "channelKey" FROM "dimChannel" '
            'WHERE "channelName" = ANY(:names)'
        ),
    },
    "dimPaymentMethod": {
        "insert": (
            'INSERT INTO "dimPaymentMethod" ("methodName", "methodType") '
            "VALUES (:methodName, :methodType) "
            'ON CONFLICT ("methodName") DO NOTHING'
        ),
        "select": (
            'SELECT "methodName", "paymentMethodKey" FROM "dimPaymentMethod" '
            'WHERE "methodName" = ANY(:names)'
        ),
    },
    "dimOrderStatus": {
        "insert": (
            'INSERT INTO "dimOrderStatus" ("statusName") '
            "VALUES (:statusName) "
            'ON CONFLICT ("statusName") DO NOTHING'
        ),
        "select": (
            'SELECT "statusName", "orderStatusKey" FROM "dimOrderStatus" '
            'WHERE "statusName" = ANY(:names)'
        ),
    },
}


class Loader:
    """Write dimension and fact DataFrames to the warehouse database."""

    def __init__(self, engine: Any, tracker: LineageTracker) -> None:
        self._engine = engine
        self._tracker = tracker

    # ------------------------------------------------------------------
    # dimDate
    # ------------------------------------------------------------------

    def upsert_dim_date(
        self, dates_df: pd.DataFrame, conn: Connection
    ) -> dict[date, int]:
        """INSERT … ON CONFLICT ("fullDate") DO NOTHING.

        Returns
        -------
        dict[date, dateKey]
        """
        if dates_df.empty:
            return {}

        rows = dates_df.to_dict(orient="records")
        conn.execute(
            text("""
                INSERT INTO "dimDate"
                    ("fullDate", year, quarter, month, "monthName",
                     "weekNumber", "dayName", "isWeekend", "isPublicHoliday")
                VALUES
                    (:fullDate, :year, :quarter, :month, :monthName,
                     :weekNumber, :dayName, :isWeekend, :isPublicHoliday)
                ON CONFLICT ("fullDate") DO NOTHING
                """),
            rows,
        )

        # Fetch the keys for all dates we just upserted
        result = conn.execute(
            text(
                'SELECT "fullDate", "dateKey" FROM "dimDate"'
                ' WHERE "fullDate" = ANY(:dates)'
            ),
            {"dates": [r["fullDate"] for r in rows]},
        )
        mapping: dict[date, int] = {row[0]: row[1] for row in result}
        log.info(
            "upsert_dim_date: %d dates upserted, %d keys fetched",
            len(rows),
            len(mapping),
        )
        return mapping

    # ------------------------------------------------------------------
    # dimProduct  (SCD Type 2)
    # ------------------------------------------------------------------

    def upsert_dim_product(
        self, products_df: pd.DataFrame, conn: Connection
    ) -> dict[str, int]:
        """SCD Type 2 upsert for dimProduct.

        * New SKUs are inserted.
        * Existing SKUs with changed productName or categoryName are expired
          (validTo = today, isCurrent = False) and a new row is inserted.

        Returns
        -------
        dict[sku, productKey]
        """
        if products_df.empty:
            return {}

        today = date.today()
        sku_to_key: dict[str, int] = {}

        for _, row in products_df.iterrows():
            sku = row["productSKU"]
            product_name = row.get("productName")
            category_name = row.get("categoryName")

            # Fetch the current active row for this SKU
            existing = conn.execute(
                text("""
                    SELECT "productKey", "productName", "categoryName"
                    FROM "dimProduct"
                    WHERE "productSKU" = :sku AND "isCurrent" = TRUE
                    LIMIT 1
                    """),
                {"sku": sku},
            ).fetchone()

            if existing is None:
                # New product — insert
                result = conn.execute(
                    text("""
                        INSERT INTO "dimProduct"
                            ("productSKU", "productName", "categoryName",
                             "validFrom", "validTo", "isCurrent")
                        VALUES
                            (:sku, :productName, :categoryName,
                             :validFrom, NULL, TRUE)
                        RETURNING "productKey"
                        """),
                    {
                        "sku": sku,
                        "productName": product_name,
                        "categoryName": category_name,
                        "validFrom": today,
                    },
                )
                sku_to_key[sku] = result.scalar()
            else:
                changed = (
                    existing.productName != product_name
                    or existing.categoryName != category_name
                )
                if changed:
                    # Expire old row
                    conn.execute(
                        text("""
                            UPDATE "dimProduct"
                            SET "validTo" = :today, "isCurrent" = FALSE
                            WHERE "productKey" = :pk
                            """),
                        {"today": today, "pk": existing.productKey},
                    )
                    # Insert new version
                    result = conn.execute(
                        text("""
                            INSERT INTO "dimProduct"
                                ("productSKU", "productName", "categoryName",
                                 "validFrom", "validTo", "isCurrent")
                            VALUES
                                (:sku, :productName, :categoryName,
                                 :validFrom, NULL, TRUE)
                            RETURNING "productKey"
                            """),
                        {
                            "sku": sku,
                            "productName": product_name,
                            "categoryName": category_name,
                            "validFrom": today,
                        },
                    )
                    sku_to_key[sku] = result.scalar()
                else:
                    sku_to_key[sku] = existing.productKey

        log.info("upsert_dim_product: %d SKUs processed", len(sku_to_key))
        return sku_to_key

    # ------------------------------------------------------------------
    # dimCustomer  (SCD Type 2)
    # ------------------------------------------------------------------

    def upsert_dim_customer(
        self, customers_df: pd.DataFrame, conn: Connection
    ) -> dict[int, int]:
        """SCD Type 2 upsert for dimCustomer.

        Returns
        -------
        dict[customerId, customerKey]
        """
        if customers_df.empty:
            return {}

        today = date.today()
        cid_to_key: dict[int, int] = {}

        for _, row in customers_df.iterrows():
            cid = int(row["customerId"])
            full_name = row.get("fullName")
            email = row.get("email")
            is_active = bool(row.get("isActive", True))

            existing = conn.execute(
                text("""
                    SELECT "customerKey", "fullName", email, "isActive"
                    FROM "dimCustomer"
                    WHERE "customerId" = :cid AND "isActive" = TRUE
                    LIMIT 1
                    """),
                {"cid": cid},
            ).fetchone()

            if existing is None:
                result = conn.execute(
                    text("""
                        INSERT INTO "dimCustomer"
                            ("customerId", "fullName", email,
                             "validFrom", "validTo", "isActive")
                        VALUES
                            (:cid, :fullName, :email,
                             :validFrom, NULL, TRUE)
                        RETURNING "customerKey"
                        """),
                    {
                        "cid": cid,
                        "fullName": full_name,
                        "email": email,
                        "validFrom": today,
                    },
                )
                cid_to_key[cid] = result.scalar()
            else:
                changed = (
                    existing.fullName != full_name
                    or existing.email != email
                    or existing.isActive != is_active
                )
                if changed:
                    conn.execute(
                        text("""
                            UPDATE "dimCustomer"
                            SET "validTo" = :today, "isActive" = FALSE
                            WHERE "customerKey" = :pk
                            """),
                        {"today": today, "pk": existing.customerKey},
                    )
                    result = conn.execute(
                        text("""
                            INSERT INTO "dimCustomer"
                                ("customerId", "fullName", email,
                                 "validFrom", "validTo", "isActive")
                            VALUES
                                (:cid, :fullName, :email,
                                 :validFrom, NULL, :isActive)
                            RETURNING "customerKey"
                            """),
                        {
                            "cid": cid,
                            "fullName": full_name,
                            "email": email,
                            "validFrom": today,
                            "isActive": is_active,
                        },
                    )
                    cid_to_key[cid] = result.scalar()
                else:
                    cid_to_key[cid] = existing.customerKey

        log.info("upsert_dim_customer: %d customers processed", len(cid_to_key))
        return cid_to_key

    # ------------------------------------------------------------------
    # Generic lookup dimension upsert
    # ------------------------------------------------------------------

    def upsert_dim_lookup(
        self,
        df: pd.DataFrame,
        table: str,
        name_col: str,
        conn: Connection,
    ) -> dict[str, int]:
        """INSERT … ON CONFLICT DO NOTHING upsert for fixed lookup dimensions.

        Covers dimStore, dimGeography, dimChannel, dimPaymentMethod,
        and dimOrderStatus.

        Returns
        -------
        dict[name_value, surrogate_key]
        """
        if df.empty:
            return {}

        config = _LOOKUP_SQL.get(table)
        if config is None:
            raise ValueError(f"Unknown lookup table: {table!r}")

        conn.execute(text(config["insert"]), df.to_dict(orient="records"))

        names = df[name_col].tolist()
        result = conn.execute(text(config["select"]), {"names": names})
        mapping: dict[str, int] = {row[0]: row[1] for row in result}
        log.info("upsert_dim_lookup(%s): %d rows processed", table, len(mapping))
        return mapping

    # ------------------------------------------------------------------
    # factSales
    # ------------------------------------------------------------------

    def load_fact_sales(
        self,
        fact_df: pd.DataFrame,
        key_maps: dict[str, Any],
        conn: Connection,
        tracker: LineageTracker,
        run_id: str,
    ) -> int:
        """Resolve FKs from key_maps and insert factSales rows.

        Parameters
        ----------
        fact_df:
            Cleansed sales DataFrame.
        key_maps:
            ``{"dates": {date: dateKey}, "products": {sku: productKey},
               "customers": {cid: customerKey}, "stores": {sid: storeKey},
               "geographies": {province: geographyKey},
               "channels": {name: channelKey},
               "payment_methods": {name: paymentMethodKey},
               "order_statuses": {name: orderStatusKey}}``
        conn:
            Active SQLAlchemy connection (within a transaction).
        tracker / run_id:
            Lineage tracking.

        Returns
        -------
        int
            Number of rows inserted.
        """
        if fact_df.empty:
            return 0

        rows = []
        for _, r in fact_df.iterrows():
            txn_dt = pd.Timestamp(r.get("transactionDatetime"))
            txn_date = txn_dt.date() if pd.notna(txn_dt) else date.today()

            date_key = key_maps["dates"].get(txn_date)
            product_key = key_maps["products"].get(r.get("productSKU"))
            store_key = key_maps.get("stores", {}).get(r.get("storeId"))
            customer_key = key_maps.get("customers", {}).get(r.get("customerId"))
            geography_key = key_maps.get("geographies", {}).get(r.get("province"))
            channel_key = key_maps.get("channels", {}).get(r.get("channel", "POS"))
            payment_method_key = key_maps.get("payment_methods", {}).get(
                r.get("paymentMethod")
            )
            order_status_key = key_maps.get("order_statuses", {}).get(
                r.get("orderStatus")
            )

            if (
                date_key is None
                or product_key is None
                or geography_key is None
                or channel_key is None
            ):
                log.debug("load_fact_sales: skipping row — missing required FK")
                continue

            rows.append(
                {
                    "dateKey": date_key,
                    "productKey": product_key,
                    "customerKey": customer_key,
                    "storeKey": store_key,
                    "geographyKey": geography_key,
                    "channelKey": channel_key,
                    "paymentMethodKey": payment_method_key,
                    "orderStatusKey": order_status_key,
                    "sourceTransactionId": str(r.get("sourceTransactionId", "")),
                    "quantity": int(r.get("quantity", 0)),
                    "unitPrice": float(r.get("unitPrice", 0)),
                    "discountApplied": float(r.get("discountApplied", 0)),
                    "grossAmount": float(r.get("grossAmount", 0)),
                    "netAmount": float(r.get("netAmount", 0)),
                }
            )

        if rows:
            conn.execute(
                text("""
                    INSERT INTO "factSales"
                        ("dateKey", "productKey", "customerKey", "storeKey",
                         "geographyKey", "channelKey", "paymentMethodKey",
                         "orderStatusKey", "sourceTransactionId",
                         quantity, "unitPrice", "discountApplied",
                         "grossAmount", "netAmount")
                    VALUES
                        (:dateKey, :productKey, :customerKey, :storeKey,
                         :geographyKey, :channelKey, :paymentMethodKey,
                         :orderStatusKey, :sourceTransactionId,
                         :quantity, :unitPrice, :discountApplied,
                         :grossAmount, :netAmount)
                    """),
                rows,
            )

        tracker.record(
            LineageEvent(
                run_id=run_id,
                step="load_fact_sales",
                source_table="posTransaction/onlineOrder",
                target_table="factSales",
                source_db=_SOURCE_DB,
                target_db=_WAREHOUSE_DB,
                rows_extracted=len(fact_df),
                rows_loaded=len(rows),
                quality_score=len(rows) / max(len(fact_df), 1),
                transformations=["FK resolution", "gross/net recompute"],
            )
        )
        log.info("load_fact_sales: %d rows inserted", len(rows))
        return len(rows)

    # ------------------------------------------------------------------
    # factFeedback
    # ------------------------------------------------------------------

    def load_fact_feedback(
        self,
        fact_df: pd.DataFrame,
        key_maps: dict[str, Any],
        conn: Connection,
        tracker: LineageTracker,
        run_id: str,
    ) -> int:
        """Resolve FKs and insert factFeedback rows.

        Returns
        -------
        int
            Number of rows inserted.
        """
        if fact_df.empty:
            return 0

        rows = []
        for _, r in fact_df.iterrows():
            sub_date = pd.Timestamp(r.get("submissionDate"))
            sub_d = sub_date.date() if pd.notna(sub_date) else date.today()

            date_key = key_maps["dates"].get(sub_d)
            customer_key = key_maps.get("customers", {}).get(r.get("customerId"))
            geography_key = key_maps.get("geographies", {}).get(r.get("province"))

            if date_key is None or customer_key is None:
                log.debug("load_fact_feedback: skipping row — missing required FK")
                continue

            free_text = r.get("freeTextComments")
            has_free_text = bool(free_text) and str(free_text).strip() != ""

            rows.append(
                {
                    "dateKey": date_key,
                    "customerKey": customer_key,
                    "productKey": None,
                    "geographyKey": geography_key,
                    "sourceOrderId": str(r.get("sourceOrderId", "")),
                    "satisfactionScore": _safe_int(r.get("satisfactionScore")),
                    "npsScore": _safe_int(r.get("npsScore")),
                    "productRating": _safe_int(r.get("productRating")),
                    "deliveryRating": _safe_int(r.get("deliveryRating")),
                    "hasFreeText": has_free_text,
                }
            )

        if rows:
            conn.execute(
                text("""
                    INSERT INTO "factFeedback"
                        ("dateKey", "customerKey", "productKey", "geographyKey",
                         "sourceOrderId", "satisfactionScore", "npsScore",
                         "productRating", "deliveryRating", "hasFreeText")
                    VALUES
                        (:dateKey, :customerKey, :productKey, :geographyKey,
                         :sourceOrderId, :satisfactionScore, :npsScore,
                         :productRating, :deliveryRating, :hasFreeText)
                    """),
                rows,
            )

        tracker.record(
            LineageEvent(
                run_id=run_id,
                step="load_fact_feedback",
                source_table="feedbackSurvey",
                target_table="factFeedback",
                source_db=_SOURCE_DB,
                target_db=_WAREHOUSE_DB,
                rows_extracted=len(fact_df),
                rows_loaded=len(rows),
                quality_score=len(rows) / max(len(fact_df), 1),
                transformations=["FK resolution", "hasFreeText flag"],
            )
        )
        log.info("load_fact_feedback: %d rows inserted", len(rows))
        return len(rows)

    # ------------------------------------------------------------------
    # factInventorySnapshot
    # ------------------------------------------------------------------

    def load_fact_inventory(
        self,
        fact_df: pd.DataFrame,
        key_maps: dict[str, Any],
        conn: Connection,
        tracker: LineageTracker,
        run_id: str,
    ) -> int:
        """Resolve FKs and insert factInventorySnapshot rows.

        Returns
        -------
        int
            Number of rows inserted.
        """
        if fact_df.empty:
            return 0

        rows = []
        snapshot_date = key_maps.get("snapshot_date", date.today())
        date_key = key_maps["dates"].get(snapshot_date)

        for _, r in fact_df.iterrows():
            product_key = key_maps.get("products", {}).get(r.get("productSKU"))
            if date_key is None or product_key is None:
                log.debug("load_fact_inventory: skipping row — missing required FK")
                continue

            stock_qty = int(r.get("stockQuantity", 0))
            reorder_thresh = int(r.get("reorderThreshold", 0))
            days_since = _safe_int(r.get("daysSinceRestock"))
            location = r.get("storeName") or r.get("province") or "unknown"

            rows.append(
                {
                    "dateKey": date_key,
                    "productKey": product_key,
                    "locationLabel": str(location),
                    "stockQuantity": stock_qty,
                    "reorderThreshold": reorder_thresh,
                    "daysSinceRestock": days_since,
                    "isBelowReorder": stock_qty < reorder_thresh,
                }
            )

        if rows:
            conn.execute(
                text("""
                    INSERT INTO "factInventorySnapshot"
                        ("dateKey", "productKey", "locationLabel", "stockQuantity",
                         "reorderThreshold", "daysSinceRestock", "isBelowReorder")
                    VALUES
                        (:dateKey, :productKey, :locationLabel, :stockQuantity,
                         :reorderThreshold, :daysSinceRestock, :isBelowReorder)
                    """),
                rows,
            )

        tracker.record(
            LineageEvent(
                run_id=run_id,
                step="load_fact_inventory",
                source_table="inventory",
                target_table="factInventorySnapshot",
                source_db=_SOURCE_DB,
                target_db=_WAREHOUSE_DB,
                rows_extracted=len(fact_df),
                rows_loaded=len(rows),
                quality_score=len(rows) / max(len(fact_df), 1),
                transformations=["FK resolution", "isBelowReorder flag"],
            )
        )
        log.info("load_fact_inventory: %d rows inserted", len(rows))
        return len(rows)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_int(value: Any) -> int | None:
    """Convert *value* to int; return None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
