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
        sql = text("""
            SELECT
                tl."lineId"                     AS "lineId",
                t."posTransactionId"            AS "sourceTransactionId",
                t."transactionDatetime"         AS "transactionDatetime",
                t."storeId"                     AS "storeId",
                s."storeName"                   AS "storeName",
                s."province"                    AS province,
                t."cashierId"                   AS "cashierId",
                c."fullName"                    AS "cashierName",
                p."productSKU"                  AS "productSKU",
                p."productName"                 AS "productName",
                cat."name"                      AS "categoryName",
                tl."quantity"                   AS quantity,
                tl."unitPrice"                  AS "unitPrice",
                tl."discountAApplied"           AS "discountApplied",
                tl."totalAmount"                AS "totalAmount"
            FROM "posTransactionLine" tl
            JOIN "posTransaction"   t   ON tl."posTransactionId" = t."posTransactionId"
            JOIN "store"            s   ON t."storeId"           = s."storeId"
            JOIN "cashier"          c   ON t."cashierId"         = c."cashierId"
            JOIN "product"          p   ON tl."productSKU"       = p."productSKU"
            JOIN "category"         cat ON p."categoryId"        = cat."categoryId"
            WHERE (:since IS NULL OR t."transactionDatetime" >= :since)
            ORDER BY t."transactionDatetime"
            """)

        with self._engine.connect() as conn:
            df = pd.read_sql(sql, conn, params={"since": since})

        log.info("extract_pos_transactions: %d rows extracted", len(df))
        return df

    # ------------------------------------------------------------------
    # Online orders
    # ------------------------------------------------------------------

    def extract_online_orders(self, since: date | None = None) -> pd.DataFrame:
        """Join onlineOrder + onlineOrderLine + product + category +
        customer + users.
        """
        sql = text("""
            SELECT
                ol."lineId"                     AS "lineId",
                o."onlineOrderId"               AS "sourceTransactionId",
                o."orderDatetime"               AS "transactionDatetime",
                o."shippingProvince"            AS province,
                o."orderStatus"                 AS "orderStatus",
                o."paymentMethod"               AS "paymentMethod",
                cu."customerId"                 AS "customerId",
                u."userName"                    AS "customerName",
                u."email"                       AS email,
                p."productSKU"                  AS "productSKU",
                p."productName"                 AS "productName",
                cat."name"                      AS "categoryName",
                ol."quantity"                   AS quantity,
                ol."unitPrice"                  AS "unitPrice",
                ol."discountApplied"            AS "discountApplied",
                ol."totalAmount"                AS "totalAmount"
            FROM "onlineOrderLine"  ol
            JOIN "onlineOrder"      o   ON ol."onlineOrderId"  = o."onlineOrderId"
            JOIN "customer"         cu  ON o."customerId"      = cu."customerId"
            JOIN "users"            u   ON cu."userId"         = u."userId"
            JOIN "product"          p   ON ol."productSKU"     = p."productSKU"
            JOIN "category"         cat ON p."categoryId"      = cat."categoryId"
            WHERE (:since IS NULL OR o."orderDatetime" >= :since)
            ORDER BY o."orderDatetime"
            """)

        with self._engine.connect() as conn:
            df = pd.read_sql(sql, conn, params={"since": since})

        log.info("extract_online_orders: %d rows extracted", len(df))
        return df

    # ------------------------------------------------------------------
    # Feedback surveys
    # ------------------------------------------------------------------

    def extract_feedback(self, since: date | None = None) -> pd.DataFrame:
        """Join feedbackSurvey + customer + users + onlineOrder."""
        sql = text("""
            SELECT
                f."responseId"                  AS "responseId",
                f."submissionDate"              AS "submissionDate",
                f."satisfactionScore"           AS "satisfactionScore",
                f."npsScore"                    AS "npsScore",
                f."productRating"               AS "productRating",
                f."deliveryRating"              AS "deliveryRating",
                f."freeTextComments"            AS "freeTextComments",
                f."onlineOrderId"               AS "sourceOrderId",
                cu."customerId"                 AS "customerId",
                u."userName"                    AS "customerName",
                u."email"                       AS email,
                o."shippingProvince"            AS province
            FROM "feedbackSurvey" f
            JOIN "customer"       cu ON f."customerId"     = cu."customerId"
            JOIN "users"          u  ON cu."userId"        = u."userId"
            JOIN "onlineOrder"    o  ON f."onlineOrderId"  = o."onlineOrderId"
            WHERE (:since IS NULL OR f."submissionDate" >= :since)
            ORDER BY f."submissionDate"
            """)

        with self._engine.connect() as conn:
            df = pd.read_sql(sql, conn, params={"since": since})

        log.info("extract_feedback: %d rows extracted", len(df))
        return df

    # ------------------------------------------------------------------
    # Inventory snapshot
    # ------------------------------------------------------------------

    def extract_inventory(self, snapshot_date: date) -> pd.DataFrame:
        """Join inventory + product + category + store; compute
        daysSinceRestock.

        Parameters
        ----------
        snapshot_date:
            The logical date for the snapshot (used to compute
            daysSinceRestock and to label the snapshot).
        """
        sql = text("""
            SELECT
                i."inventoryId"                 AS "inventoryId",
                i."productSKU"                  AS "productSKU",
                p."productName"                 AS "productName",
                cat."name"                      AS "categoryName",
                i."currentStockQty"             AS "stockQuantity",
                i."reorderThreshold"            AS "reorderThreshold",
                i."lastRestockedDate"           AS "lastRestockedDate",
                (:snapshot_date::date - i."lastRestockedDate")
                                                AS "daysSinceRestock",
                s."storeId"                     AS "storeId",
                s."storeName"                   AS "storeName",
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
