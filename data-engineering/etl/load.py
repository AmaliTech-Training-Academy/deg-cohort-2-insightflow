"""Load module — writes transformed data to the OLAP warehouse."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import pandas as pd
from etl.lineage import LineageEvent, LineageTracker
from psycopg2.extras import execute_values
from sqlalchemy import text
from sqlalchemy.engine import Connection

log = logging.getLogger("insightflow.load")

_SOURCE_DB = "insightflow_app"
_WAREHOUSE_DB = "insightflow_star_schema"

# Rows per round-trip for bulk inserts.
_BATCH_SIZE = 1000

# Static SQL for each lookup dimension — avoids dynamic string construction.
# All identifiers are literals; no user input reaches these strings.
_LOOKUP_SQL: dict[str, dict[str, str]] = {
    "dimStore": {
        "insert": (
            'INSERT INTO "dimStore" ("storeId", "storeName", "province") '
            "VALUES %s "
            'ON CONFLICT ("storeId") DO NOTHING'
        ),
        "template": "(%(storeId)s, %(storeName)s, %(province)s)",
        "select": (
            'SELECT "storeId", "storeKey" FROM "dimStore" '
            'WHERE "storeId" = ANY(:names)'
        ),
    },
    "dimGeography": {
        "insert": (
            'INSERT INTO "dimGeography" ("province", "country") '
            "VALUES %s "
            'ON CONFLICT ("province", "country") DO NOTHING'
        ),
        "template": "(%(province)s, %(country)s)",
        "select": (
            'SELECT "province", "geographyKey" FROM "dimGeography" '
            'WHERE "province" = ANY(:names)'
        ),
    },
    "dimChannel": {
        "insert": (
            'INSERT INTO "dimChannel" ("channelName", "channelType") '
            "VALUES %s "
            'ON CONFLICT ("channelName") DO NOTHING'
        ),
        "template": "(%(channelName)s, %(channelType)s)",
        "select": (
            'SELECT "channelName", "channelKey" FROM "dimChannel" '
            'WHERE "channelName" = ANY(:names)'
        ),
    },
    "dimPaymentMethod": {
        "insert": (
            'INSERT INTO "dimPaymentMethod" ("methodName", "methodType") '
            "VALUES %s "
            'ON CONFLICT ("methodName") DO NOTHING'
        ),
        "template": "(%(methodName)s, %(methodType)s)",
        "select": (
            'SELECT "methodName", "paymentMethodKey" FROM "dimPaymentMethod" '
            'WHERE "methodName" = ANY(:names)'
        ),
    },
    "dimOrderStatus": {
        "insert": (
            'INSERT INTO "dimOrderStatus" ("statusName") '
            "VALUES %s "
            'ON CONFLICT ("statusName") DO NOTHING'
        ),
        "template": "(%(statusName)s,)",
        "select": (
            'SELECT "statusName", "orderStatusKey" FROM "dimOrderStatus" '
            'WHERE "statusName" = ANY(:names)'
        ),
    },
}


def _bulk_insert(
    conn: Connection,
    sql: str,
    rows: list[dict],
    template: str,
    fetch: bool = False,
) -> list[tuple]:
    """Bulk INSERT via psycopg2 execute_values.

    Generates one ``INSERT ... VALUES (...), (...), ...`` per *_BATCH_SIZE*
    rows instead of one round-trip per row, cutting load time dramatically
    for large datasets against remote databases.

    Parameters
    ----------
    conn:
        Active SQLAlchemy connection (within a transaction).
    sql:
        INSERT statement using ``%s`` as the values placeholder.
    rows:
        List of parameter dicts.
    template:
        psycopg2 row template, e.g. ``"(%(col1)s, %(col2)s)"``.
    fetch:
        When True, return rows produced by a ``RETURNING`` clause.
    """
    cursor = conn.connection.cursor()
    execute_values(
        cursor, sql, rows, template=template, page_size=_BATCH_SIZE, fetch=fetch
    )
    if fetch:
        return list(cursor.fetchall())
    return []


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
        """Bulk INSERT … ON CONFLICT ("fullDate") DO NOTHING.

        Returns
        -------
        dict[date, dateKey]
        """
        if dates_df.empty:
            return {}

        rows = dates_df.to_dict(orient="records")
        _bulk_insert(
            conn,
            sql=(
                'INSERT INTO "dimDate" '
                '("fullDate", year, quarter, month, "monthName", '
                '"weekNumber", "dayName", "isWeekend", "isPublicHoliday") '
                "VALUES %s "
                'ON CONFLICT ("fullDate") DO NOTHING'
            ),
            rows=rows,
            template=(
                "(%(fullDate)s, %(year)s, %(quarter)s, %(month)s, %(monthName)s,"
                " %(weekNumber)s, %(dayName)s, %(isWeekend)s, %(isPublicHoliday)s)"
            ),
        )

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
        """SCD Type 2 upsert for dimProduct — batched.

        Fetches all existing active records in ONE query, compares in Python,
        then issues a single bulk UPDATE (expire changed rows) and a single
        bulk INSERT (new rows + new versions), returning the key mapping.

        Returns
        -------
        dict[sku, productKey]
        """
        if products_df.empty:
            return {}

        today = date.today()
        skus = products_df["productSKU"].tolist()

        # 1. Fetch ALL current active rows for all SKUs in one query.
        result = conn.execute(
            text("""
                SELECT "productKey", "productSKU", "productName", "categoryName"
                FROM "dimProduct"
                WHERE "productSKU" = ANY(:skus) AND "isCurrent" = TRUE
            """),
            {"skus": skus},
        )
        existing: dict[str, Any] = {row.productSKU: row for row in result}

        # 2. Classify each row in Python.
        to_expire: list[int] = []
        to_insert: list[dict] = []
        sku_to_key: dict[str, int] = {}

        for _, row in products_df.iterrows():
            sku = row["productSKU"]
            product_name = row.get("productName")
            category_name = row.get("categoryName")

            if sku not in existing:
                to_insert.append(
                    {
                        "sku": sku,
                        "productName": product_name,
                        "categoryName": category_name,
                        "validFrom": today,
                    }
                )
            else:
                ex = existing[sku]
                if ex.productName != product_name or ex.categoryName != category_name:
                    to_expire.append(ex.productKey)
                    to_insert.append(
                        {
                            "sku": sku,
                            "productName": product_name,
                            "categoryName": category_name,
                            "validFrom": today,
                        }
                    )
                else:
                    sku_to_key[sku] = ex.productKey

        # 3. Expire changed rows in ONE UPDATE.
        if to_expire:
            conn.execute(
                text("""
                    UPDATE "dimProduct"
                    SET "validTo" = :today, "isCurrent" = FALSE
                    WHERE "productKey" = ANY(:keys)
                """),
                {"today": today, "keys": to_expire},
            )

        # 4. Bulk INSERT new rows, get back SKU → key via RETURNING.
        if to_insert:
            returned = _bulk_insert(
                conn,
                sql=(
                    'INSERT INTO "dimProduct" '
                    '("productSKU", "productName", "categoryName",'
                    ' "validFrom", "validTo", "isCurrent") '
                    "VALUES %s "
                    'RETURNING "productSKU", "productKey"'
                ),
                rows=to_insert,
                template=(
                    "(%(sku)s, %(productName)s, %(categoryName)s,"
                    " %(validFrom)s, NULL, TRUE)"
                ),
                fetch=True,
            )
            for sku, key in returned:
                sku_to_key[sku] = key

        log.info("upsert_dim_product: %d SKUs processed", len(sku_to_key))
        return sku_to_key

    # ------------------------------------------------------------------
    # dimCustomer  (SCD Type 2)
    # ------------------------------------------------------------------

    def upsert_dim_customer(
        self, customers_df: pd.DataFrame, conn: Connection
    ) -> dict[str, int]:
        """SCD Type 2 upsert for dimCustomer — batched.

        Returns
        -------
        dict[customerId, customerKey]
        """
        if customers_df.empty:
            return {}

        today = date.today()
        cids = customers_df["customerId"].astype(str).tolist()

        # 1. Fetch all current active rows in one query.
        result = conn.execute(
            text("""
                SELECT "customerKey", "customerId", "fullName", email, "isActive"
                FROM "dimCustomer"
                WHERE "customerId" = ANY(:cids) AND "isActive" = TRUE
            """),
            {"cids": cids},
        )
        existing: dict[str, Any] = {str(row.customerId): row for row in result}

        # 2. Classify in Python.
        to_expire: list[int] = []
        to_insert: list[dict] = []
        cid_to_key: dict[str, int] = {}

        for _, row in customers_df.iterrows():
            cid = str(row["customerId"])
            full_name = row.get("fullName")
            email = row.get("email")
            is_active = bool(row.get("isActive", True))

            if cid not in existing:
                to_insert.append(
                    {
                        "cid": cid,
                        "fullName": full_name,
                        "email": email,
                        "validFrom": today,
                        "isActive": is_active,
                    }
                )
            else:
                ex = existing[cid]
                if (
                    ex.fullName != full_name
                    or ex.email != email
                    or ex.isActive != is_active
                ):
                    to_expire.append(ex.customerKey)
                    to_insert.append(
                        {
                            "cid": cid,
                            "fullName": full_name,
                            "email": email,
                            "validFrom": today,
                            "isActive": is_active,
                        }
                    )
                else:
                    cid_to_key[cid] = ex.customerKey

        # 3. Expire changed rows in ONE UPDATE.
        if to_expire:
            conn.execute(
                text("""
                    UPDATE "dimCustomer"
                    SET "validTo" = :today, "isActive" = FALSE
                    WHERE "customerKey" = ANY(:keys)
                """),
                {"today": today, "keys": to_expire},
            )

        # 4. Bulk INSERT, get keys back via RETURNING.
        if to_insert:
            returned = _bulk_insert(
                conn,
                sql=(
                    'INSERT INTO "dimCustomer" '
                    '("customerId", "fullName", email,'
                    ' "validFrom", "validTo", "isActive") '
                    "VALUES %s "
                    'RETURNING "customerId", "customerKey"'
                ),
                rows=to_insert,
                template=(
                    "(%(cid)s, %(fullName)s, %(email)s,"
                    " %(validFrom)s, NULL, %(isActive)s)"
                ),
                fetch=True,
            )
            for cid, key in returned:
                cid_to_key[str(cid)] = key

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
        """Bulk INSERT … ON CONFLICT DO NOTHING for fixed lookup dimensions.

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

        _bulk_insert(
            conn,
            sql=config["insert"],
            rows=df.to_dict(orient="records"),
            template=config["template"],
        )

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
        """Resolve FKs from key_maps and bulk-insert factSales rows.

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
            _bulk_insert(
                conn,
                sql=(
                    'INSERT INTO "factSales" '
                    '("dateKey", "productKey", "customerKey", "storeKey",'
                    ' "geographyKey", "channelKey", "paymentMethodKey",'
                    ' "orderStatusKey", "sourceTransactionId",'
                    ' quantity, "unitPrice", "discountApplied",'
                    ' "grossAmount", "netAmount") '
                    "VALUES %s"
                ),
                rows=rows,
                template=(
                    "(%(dateKey)s, %(productKey)s, %(customerKey)s, %(storeKey)s,"
                    " %(geographyKey)s, %(channelKey)s, %(paymentMethodKey)s,"
                    " %(orderStatusKey)s, %(sourceTransactionId)s,"
                    " %(quantity)s, %(unitPrice)s, %(discountApplied)s,"
                    " %(grossAmount)s, %(netAmount)s)"
                ),
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
        """Resolve FKs and bulk-insert factFeedback rows.

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
            _bulk_insert(
                conn,
                sql=(
                    'INSERT INTO "factFeedback" '
                    '("dateKey", "customerKey", "productKey", "geographyKey",'
                    ' "sourceOrderId", "satisfactionScore", "npsScore",'
                    ' "productRating", "deliveryRating", "hasFreeText") '
                    "VALUES %s"
                ),
                rows=rows,
                template=(
                    "(%(dateKey)s, %(customerKey)s, %(productKey)s, %(geographyKey)s,"
                    " %(sourceOrderId)s, %(satisfactionScore)s, %(npsScore)s,"
                    " %(productRating)s, %(deliveryRating)s, %(hasFreeText)s)"
                ),
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
        """Resolve FKs and bulk-insert factInventorySnapshot rows.

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
            _bulk_insert(
                conn,
                sql=(
                    'INSERT INTO "factInventorySnapshot" '
                    '("dateKey", "productKey", "locationLabel", "stockQuantity",'
                    ' "reorderThreshold", "daysSinceRestock", "isBelowReorder") '
                    "VALUES %s"
                ),
                rows=rows,
                template=(
                    "(%(dateKey)s, %(productKey)s, %(locationLabel)s,"
                    " %(stockQuantity)s, %(reorderThreshold)s,"
                    " %(daysSinceRestock)s, %(isBelowReorder)s)"
                ),
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
