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


class Loader:
    """Write dimension and fact DataFrames to the warehouse database."""

    def __init__(self, engine: Any, tracker: LineageTracker) -> None:
        self._engine = engine
        self._tracker = tracker

    # ------------------------------------------------------------------
    # dim_date
    # ------------------------------------------------------------------

    def upsert_dim_date(
        self, dates_df: pd.DataFrame, conn: Connection
    ) -> dict[date, int]:
        """INSERT … ON CONFLICT (full_date) DO NOTHING.

        Returns
        -------
        dict[date, date_key]
        """
        if dates_df.empty:
            return {}

        rows = dates_df.to_dict(orient="records")
        conn.execute(
            text("""
                INSERT INTO dim_date
                    (full_date, year, quarter, month, month_name,
                     week_number, day_name, is_weekend, is_public_holiday)
                VALUES
                    (:full_date, :year, :quarter, :month, :month_name,
                     :week_number, :day_name, :is_weekend, :is_public_holiday)
                ON CONFLICT (full_date) DO NOTHING
                """),
            rows,
        )

        # Fetch the keys for all dates we just upserted
        result = conn.execute(
            text(
                "SELECT full_date, date_key FROM dim_date WHERE full_date = ANY(:dates)"
            ),
            {"dates": [r["full_date"] for r in rows]},
        )
        mapping: dict[date, int] = {row.full_date: row.date_key for row in result}
        log.info(
            "upsert_dim_date: %d dates upserted, %d keys fetched",
            len(rows),
            len(mapping),
        )
        return mapping

    # ------------------------------------------------------------------
    # dim_product  (SCD Type 2)
    # ------------------------------------------------------------------

    def upsert_dim_product(
        self, products_df: pd.DataFrame, conn: Connection
    ) -> dict[str, int]:
        """SCD Type 2 upsert for dim_product.

        * New SKUs are inserted.
        * Existing SKUs with changed product_name or category_name are expired
          (valid_to = today, is_current = False) and a new row is inserted.

        Returns
        -------
        dict[sku, product_key]
        """
        if products_df.empty:
            return {}

        today = date.today()
        sku_to_key: dict[str, int] = {}

        for _, row in products_df.iterrows():
            sku = row["product_sku"]
            product_name = row.get("product_name")
            category_name = row.get("category_name")

            # Fetch the current active row for this SKU
            existing = conn.execute(
                text("""
                    SELECT product_key, product_name, category_name
                    FROM dim_product
                    WHERE product_sku = :sku AND is_current = TRUE
                    LIMIT 1
                    """),
                {"sku": sku},
            ).fetchone()

            if existing is None:
                # New product — insert
                result = conn.execute(
                    text("""
                        INSERT INTO dim_product
                            (product_sku, product_name, category_name,
                             valid_from, valid_to, is_current)
                        VALUES
                            (:sku, :product_name, :category_name,
                             :valid_from, NULL, TRUE)
                        RETURNING product_key
                        """),
                    {
                        "sku": sku,
                        "product_name": product_name,
                        "category_name": category_name,
                        "valid_from": today,
                    },
                )
                sku_to_key[sku] = result.scalar()
            else:
                changed = (
                    existing.product_name != product_name
                    or existing.category_name != category_name
                )
                if changed:
                    # Expire old row
                    conn.execute(
                        text("""
                            UPDATE dim_product
                            SET valid_to = :today, is_current = FALSE
                            WHERE product_key = :pk
                            """),
                        {"today": today, "pk": existing.product_key},
                    )
                    # Insert new version
                    result = conn.execute(
                        text("""
                            INSERT INTO dim_product
                                (product_sku, product_name, category_name,
                                 valid_from, valid_to, is_current)
                            VALUES
                                (:sku, :product_name, :category_name,
                                 :valid_from, NULL, TRUE)
                            RETURNING product_key
                            """),
                        {
                            "sku": sku,
                            "product_name": product_name,
                            "category_name": category_name,
                            "valid_from": today,
                        },
                    )
                    sku_to_key[sku] = result.scalar()
                else:
                    sku_to_key[sku] = existing.product_key

        log.info("upsert_dim_product: %d SKUs processed", len(sku_to_key))
        return sku_to_key

    # ------------------------------------------------------------------
    # dim_customer  (SCD Type 2)
    # ------------------------------------------------------------------

    def upsert_dim_customer(
        self, customers_df: pd.DataFrame, conn: Connection
    ) -> dict[int, int]:
        """SCD Type 2 upsert for dim_customer.

        Returns
        -------
        dict[customer_id, customer_key]
        """
        if customers_df.empty:
            return {}

        today = date.today()
        cid_to_key: dict[int, int] = {}

        for _, row in customers_df.iterrows():
            cid = int(row["customer_id"])
            full_name = row.get("full_name")
            email = row.get("email")
            is_active = bool(row.get("is_active", True))

            existing = conn.execute(
                text("""
                    SELECT customer_key, full_name, email, is_active
                    FROM dim_customer
                    WHERE customer_id = :cid AND is_active = TRUE
                    LIMIT 1
                    """),
                {"cid": cid},
            ).fetchone()

            if existing is None:
                result = conn.execute(
                    text("""
                        INSERT INTO dim_customer
                            (customer_id, full_name, email,
                             valid_from, valid_to, is_active)
                        VALUES
                            (:cid, :full_name, :email,
                             :valid_from, NULL, TRUE)
                        RETURNING customer_key
                        """),
                    {
                        "cid": cid,
                        "full_name": full_name,
                        "email": email,
                        "valid_from": today,
                    },
                )
                cid_to_key[cid] = result.scalar()
            else:
                changed = (
                    existing.full_name != full_name
                    or existing.email != email
                    or existing.is_active != is_active
                )
                if changed:
                    conn.execute(
                        text("""
                            UPDATE dim_customer
                            SET valid_to = :today, is_active = FALSE
                            WHERE customer_key = :pk
                            """),
                        {"today": today, "pk": existing.customer_key},
                    )
                    result = conn.execute(
                        text("""
                            INSERT INTO dim_customer
                                (customer_id, full_name, email,
                                 valid_from, valid_to, is_active)
                            VALUES
                                (:cid, :full_name, :email,
                                 :valid_from, NULL, :is_active)
                            RETURNING customer_key
                            """),
                        {
                            "cid": cid,
                            "full_name": full_name,
                            "email": email,
                            "valid_from": today,
                            "is_active": is_active,
                        },
                    )
                    cid_to_key[cid] = result.scalar()
                else:
                    cid_to_key[cid] = existing.customer_key

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
        """Generic INSERT … ON CONFLICT (name_col) DO NOTHING upsert.

        Covers dim_store, dim_geography, dim_channel, dim_payment_method,
        and dim_order_status.

        Returns
        -------
        dict[name_value, surrogate_key]
        """
        if df.empty:
            return {}

        _TABLE_KEY_MAP: dict[str, str] = {
            "dim_store": "store_key",
            "dim_geography": "geography_key",
            "dim_channel": "channel_key",
            "dim_payment_method": "payment_method_key",
            "dim_order_status": "order_status_key",
        }
        pk_col = _TABLE_KEY_MAP.get(table, f"{table.replace('dim_', '')}_key")

        # Build column list from df
        cols = list(df.columns)
        col_list = ", ".join(cols)
        bind_list = ", ".join(f":{c}" for c in cols)

        conn.execute(
            text(f"""
                INSERT INTO {table} ({col_list})
                VALUES ({bind_list})
                ON CONFLICT ({name_col}) DO NOTHING
                """),
            df.to_dict(orient="records"),
        )

        # Fetch keys
        names = df[name_col].tolist()
        result = conn.execute(
            text(
                f"SELECT {name_col}, {pk_col} FROM {table}"
                f" WHERE {name_col} = ANY(:names)"
            ),
            {"names": names},
        )
        mapping: dict[str, int] = {row[0]: row[1] for row in result}
        log.info("upsert_dim_lookup(%s): %d rows processed", table, len(mapping))
        return mapping

    # ------------------------------------------------------------------
    # fact_sales
    # ------------------------------------------------------------------

    def load_fact_sales(
        self,
        fact_df: pd.DataFrame,
        key_maps: dict[str, Any],
        conn: Connection,
        tracker: LineageTracker,
        run_id: str,
    ) -> int:
        """Resolve FKs from key_maps and insert fact_sales rows.

        Parameters
        ----------
        fact_df:
            Cleansed sales DataFrame.
        key_maps:
            ``{"dates": {date: date_key}, "products": {sku: product_key},
               "customers": {cid: customer_key}, "stores": {sid: store_key},
               "geographies": {province: geography_key},
               "channels": {name: channel_key},
               "payment_methods": {name: payment_method_key},
               "order_statuses": {name: order_status_key}}``
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
            txn_dt = pd.Timestamp(r.get("transaction_datetime"))
            txn_date = txn_dt.date() if pd.notna(txn_dt) else date.today()

            date_key = key_maps["dates"].get(txn_date)
            product_key = key_maps["products"].get(r.get("product_sku"))
            store_key = key_maps.get("stores", {}).get(r.get("store_id"))
            customer_key = key_maps.get("customers", {}).get(r.get("customer_id"))
            geography_key = key_maps.get("geographies", {}).get(r.get("province"))
            channel_key = key_maps.get("channels", {}).get(r.get("channel", "POS"))
            payment_method_key = key_maps.get("payment_methods", {}).get(
                r.get("payment_method")
            )
            order_status_key = key_maps.get("order_statuses", {}).get(
                r.get("order_status")
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
                    "date_key": date_key,
                    "product_key": product_key,
                    "customer_key": customer_key,
                    "store_key": store_key,
                    "geography_key": geography_key,
                    "channel_key": channel_key,
                    "payment_method_key": payment_method_key,
                    "order_status_key": order_status_key,
                    "source_transaction_id": str(r.get("source_transaction_id", "")),
                    "quantity": int(r.get("quantity", 0)),
                    "unit_price": float(r.get("unit_price", 0)),
                    "discount_applied": float(r.get("discount_applied", 0)),
                    "gross_amount": float(r.get("gross_amount", 0)),
                    "net_amount": float(r.get("net_amount", 0)),
                }
            )

        if rows:
            conn.execute(
                text("""
                    INSERT INTO fact_sales
                        (date_key, product_key, customer_key, store_key,
                         geography_key, channel_key, payment_method_key,
                         order_status_key, source_transaction_id,
                         quantity, unit_price, discount_applied,
                         gross_amount, net_amount)
                    VALUES
                        (:date_key, :product_key, :customer_key, :store_key,
                         :geography_key, :channel_key, :payment_method_key,
                         :order_status_key, :source_transaction_id,
                         :quantity, :unit_price, :discount_applied,
                         :gross_amount, :net_amount)
                    """),
                rows,
            )

        tracker.record(
            LineageEvent(
                run_id=run_id,
                step="load_fact_sales",
                source_table="posTransaction/onlineOrder",
                target_table="fact_sales",
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
    # fact_feedback
    # ------------------------------------------------------------------

    def load_fact_feedback(
        self,
        fact_df: pd.DataFrame,
        key_maps: dict[str, Any],
        conn: Connection,
        tracker: LineageTracker,
        run_id: str,
    ) -> int:
        """Resolve FKs and insert fact_feedback rows.

        Returns
        -------
        int
            Number of rows inserted.
        """
        if fact_df.empty:
            return 0

        rows = []
        for _, r in fact_df.iterrows():
            sub_date = pd.Timestamp(r.get("submission_date"))
            sub_d = sub_date.date() if pd.notna(sub_date) else date.today()

            date_key = key_maps["dates"].get(sub_d)
            customer_key = key_maps.get("customers", {}).get(r.get("customer_id"))
            geography_key = key_maps.get("geographies", {}).get(r.get("province"))

            if date_key is None or customer_key is None:
                log.debug("load_fact_feedback: skipping row — missing required FK")
                continue

            free_text = r.get("free_text_comments")
            has_free_text = bool(free_text) and str(free_text).strip() != ""

            rows.append(
                {
                    "date_key": date_key,
                    "customer_key": customer_key,
                    "product_key": None,
                    "geography_key": geography_key,
                    "source_order_id": str(r.get("source_order_id", "")),
                    "satisfaction_score": _safe_int(r.get("satisfaction_score")),
                    "nps_score": _safe_int(r.get("nps_score")),
                    "product_rating": _safe_int(r.get("product_rating")),
                    "delivery_rating": _safe_int(r.get("delivery_rating")),
                    "has_free_text": has_free_text,
                }
            )

        if rows:
            conn.execute(
                text("""
                    INSERT INTO fact_feedback
                        (date_key, customer_key, product_key, geography_key,
                         source_order_id, satisfaction_score, nps_score,
                         product_rating, delivery_rating, has_free_text)
                    VALUES
                        (:date_key, :customer_key, :product_key, :geography_key,
                         :source_order_id, :satisfaction_score, :nps_score,
                         :product_rating, :delivery_rating, :has_free_text)
                    """),
                rows,
            )

        tracker.record(
            LineageEvent(
                run_id=run_id,
                step="load_fact_feedback",
                source_table="feedbackSurvey",
                target_table="fact_feedback",
                source_db=_SOURCE_DB,
                target_db=_WAREHOUSE_DB,
                rows_extracted=len(fact_df),
                rows_loaded=len(rows),
                quality_score=len(rows) / max(len(fact_df), 1),
                transformations=["FK resolution", "has_free_text flag"],
            )
        )
        log.info("load_fact_feedback: %d rows inserted", len(rows))
        return len(rows)

    # ------------------------------------------------------------------
    # fact_inventory_snapshot
    # ------------------------------------------------------------------

    def load_fact_inventory(
        self,
        fact_df: pd.DataFrame,
        key_maps: dict[str, Any],
        conn: Connection,
        tracker: LineageTracker,
        run_id: str,
    ) -> int:
        """Resolve FKs and insert fact_inventory_snapshot rows.

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
            product_key = key_maps.get("products", {}).get(r.get("product_sku"))
            if date_key is None or product_key is None:
                log.debug("load_fact_inventory: skipping row — missing required FK")
                continue

            stock_qty = int(r.get("stock_quantity", 0))
            reorder_thresh = int(r.get("reorder_threshold", 0))
            days_since = _safe_int(r.get("days_since_restock"))
            location = r.get("store_name") or r.get("province") or "unknown"

            rows.append(
                {
                    "date_key": date_key,
                    "product_key": product_key,
                    "location_label": str(location),
                    "stock_quantity": stock_qty,
                    "reorder_threshold": reorder_thresh,
                    "days_since_restock": days_since,
                    "is_below_reorder": stock_qty < reorder_thresh,
                }
            )

        if rows:
            conn.execute(
                text("""
                    INSERT INTO fact_inventory_snapshot
                        (date_key, product_key, location_label, stock_quantity,
                         reorder_threshold, days_since_restock, is_below_reorder)
                    VALUES
                        (:date_key, :product_key, :location_label, :stock_quantity,
                         :reorder_threshold, :days_since_restock, :is_below_reorder)
                    """),
                rows,
            )

        tracker.record(
            LineageEvent(
                run_id=run_id,
                step="load_fact_inventory",
                source_table="inventory",
                target_table="fact_inventory_snapshot",
                source_db=_SOURCE_DB,
                target_db=_WAREHOUSE_DB,
                rows_extracted=len(fact_df),
                rows_loaded=len(rows),
                quality_score=len(rows) / max(len(fact_df), 1),
                transformations=["FK resolution", "is_below_reorder flag"],
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
