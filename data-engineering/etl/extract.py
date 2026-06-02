"""Extraction module — reads from the OLTP source database."""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

log = logging.getLogger("insightflow.extract")


class Extractor:
    """Extract raw data from the OLTP source database."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # ------------------------------------------------------------------
    # POS transactions
    # ------------------------------------------------------------------

    def extract_pos_transactions(self, since: date | None = None) -> pd.DataFrame:
        """Join posTransaction + posTransactionLine + product + category +
        store + cashier.

        Parameters
        ----------
        since:
            If provided, only rows where transactionDatetime >= since are
            returned (incremental load).
        """
        since_filter = ""
        params: dict = {}
        if since is not None:
            since_filter = 'AND t."transactionDatetime" >= :since'
            params["since"] = since

        sql = text(f"""
            SELECT
                tl."lineId"                     AS line_id,
                t."posTransactionId"            AS source_transaction_id,
                t."transactionDatetime"         AS transaction_datetime,
                t."storeId"                     AS store_id,
                s."storeName"                   AS store_name,
                s."province"                    AS province,
                t."cashierId"                   AS cashier_id,
                c."fullName"                    AS cashier_name,
                p."productSKU"                  AS product_sku,
                p."productName"                 AS product_name,
                cat."name"                      AS category_name,
                tl."quantity"                   AS quantity,
                tl."unitPrice"                  AS unit_price,
                tl."discountAApplied"           AS discount_applied,
                tl."totalAmount"                AS total_amount
            FROM "posTransactionLine" tl
            JOIN "posTransaction"   t   ON tl."posTransactionId" = t."posTransactionId"
            JOIN "store"            s   ON t."storeId"           = s."storeId"
            JOIN "cashier"          c   ON t."cashierId"         = c."cashierId"
            JOIN "product"          p   ON tl."productSKU"       = p."productSKU"
            JOIN "category"         cat ON p."categoryId"        = cat."categoryId"
            WHERE 1=1
            {since_filter}
            ORDER BY t."transactionDatetime"
            """)

        with self._engine.connect() as conn:
            df = pd.read_sql(sql, conn, params=params)

        log.info("extract_pos_transactions: %d rows extracted", len(df))
        return df

    # ------------------------------------------------------------------
    # Online orders
    # ------------------------------------------------------------------

    def extract_online_orders(self, since: date | None = None) -> pd.DataFrame:
        """Join onlineOrder + onlineOrderLine + product + category +
        customer + users.
        """
        since_filter = ""
        params: dict = {}
        if since is not None:
            since_filter = 'AND o."orderDatetime" >= :since'
            params["since"] = since

        sql = text(f"""
            SELECT
                ol."lineId"                     AS line_id,
                o."onlineOrderId"               AS source_transaction_id,
                o."orderDatetime"               AS transaction_datetime,
                o."shippingProvince"            AS province,
                o."orderStatus"                 AS order_status,
                o."paymentMethod"               AS payment_method,
                cu."customerId"                 AS customer_id,
                u."userName"                    AS customer_name,
                u."email"                       AS email,
                p."productSKU"                  AS product_sku,
                p."productName"                 AS product_name,
                cat."name"                      AS category_name,
                ol."quantity"                   AS quantity,
                ol."unitPrice"                  AS unit_price,
                ol."discountApplied"            AS discount_applied,
                ol."totalAmount"                AS total_amount
            FROM "onlineOrderLine"  ol
            JOIN "onlineOrder"      o   ON ol."onlineOrderId"  = o."onlineOrderId"
            JOIN "customer"         cu  ON o."customerId"      = cu."customerId"
            JOIN "users"            u   ON cu."userId"         = u."userId"
            JOIN "product"          p   ON ol."productSKU"     = p."productSKU"
            JOIN "category"         cat ON p."categoryId"      = cat."categoryId"
            WHERE 1=1
            {since_filter}
            ORDER BY o."orderDatetime"
            """)

        with self._engine.connect() as conn:
            df = pd.read_sql(sql, conn, params=params)

        log.info("extract_online_orders: %d rows extracted", len(df))
        return df

    # ------------------------------------------------------------------
    # Feedback surveys
    # ------------------------------------------------------------------

    def extract_feedback(self, since: date | None = None) -> pd.DataFrame:
        """Join feedbackSurvey + customer + users + onlineOrder."""
        since_filter = ""
        params: dict = {}
        if since is not None:
            since_filter = 'AND f."submissionDate" >= :since'
            params["since"] = since

        sql = text(f"""
            SELECT
                f."responseId"                  AS response_id,
                f."submissionDate"              AS submission_date,
                f."satisfactionScore"           AS satisfaction_score,
                f."npsScore"                    AS nps_score,
                f."productRating"               AS product_rating,
                f."deliveryRating"              AS delivery_rating,
                f."freeTextComments"            AS free_text_comments,
                f."onlineOrderId"               AS source_order_id,
                cu."customerId"                 AS customer_id,
                u."userName"                    AS customer_name,
                u."email"                       AS email,
                o."shippingProvince"            AS province
            FROM "feedbackSurvey" f
            JOIN "customer"       cu ON f."customerId"     = cu."customerId"
            JOIN "users"          u  ON cu."userId"        = u."userId"
            JOIN "onlineOrder"    o  ON f."onlineOrderId"  = o."onlineOrderId"
            WHERE 1=1
            {since_filter}
            ORDER BY f."submissionDate"
            """)

        with self._engine.connect() as conn:
            df = pd.read_sql(sql, conn, params=params)

        log.info("extract_feedback: %d rows extracted", len(df))
        return df

    # ------------------------------------------------------------------
    # Inventory snapshot
    # ------------------------------------------------------------------

    def extract_inventory(self, snapshot_date: date) -> pd.DataFrame:
        """Join inventory + product + category + store; compute
        days_since_restock.

        Parameters
        ----------
        snapshot_date:
            The logical date for the snapshot (used to compute
            days_since_restock and to label the snapshot).
        """
        sql = text("""
            SELECT
                i."inventoryId"                 AS inventory_id,
                i."productSKU"                  AS product_sku,
                p."productName"                 AS product_name,
                cat."name"                      AS category_name,
                i."currentStockQty"             AS stock_quantity,
                i."reorderThreshold"            AS reorder_threshold,
                i."lastRestockedDate"           AS last_restocked_date,
                (:snapshot_date::date - i."lastRestockedDate")
                                                AS days_since_restock,
                s."storeId"                     AS store_id,
                s."storeName"                   AS store_name,
                s."province"                    AS province
            FROM "inventory"  i
            JOIN "product"    p   ON i."productSKU"   = p."productSKU"
            JOIN "category"   cat ON p."categoryId"   = cat."categoryId"
            LEFT JOIN "store" s   ON s."storeId" = (
                SELECT MIN("storeId") FROM "store"
            )
            ORDER BY i."productSKU"
            """)

        with self._engine.connect() as conn:
            df = pd.read_sql(sql, conn, params={"snapshot_date": snapshot_date})

        log.info(
            "extract_inventory: %d rows extracted for snapshot_date=%s",
            len(df),
            snapshot_date,
        )
        return df
