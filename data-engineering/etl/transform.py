"""Transformation module for the InsightFlow ETL pipeline.

Builds dimension and fact DataFrames from cleansed OLTP extracts.
All methods operate purely on pandas DataFrames — no database I/O.
"""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd

log = logging.getLogger("insightflow.transform")

_COUNTRY_DEFAULT = "Ghana"

# Public holidays — extend as needed (YYYY-MM-DD strings)
_PUBLIC_HOLIDAYS: frozenset[str] = frozenset(
    {
        "2024-01-01",
        "2024-03-06",
        "2024-04-05",
        "2024-05-01",
        "2024-07-01",
        "2024-12-25",
        "2024-12-26",
        "2024-02-01",
        "2024-04-07",
        "2024-07-04",
    }
)


class Transformer:
    """Pure-pandas transformation helpers for building star-schema objects."""

    # ------------------------------------------------------------------
    # dim_date
    # ------------------------------------------------------------------

    def build_dim_date(self, dates: list[date]) -> pd.DataFrame:
        """Generate dim_date rows for each unique date in *dates*.

        Parameters
        ----------
        dates:
            Collection of :class:`datetime.date` objects (duplicates OK).

        Returns
        -------
        pd.DataFrame
            Columns: full_date, year, quarter, month, month_name,
            week_number, day_name, is_weekend, is_public_holiday.
        """
        unique_dates = sorted(set(d for d in dates if d is not None))
        records = []
        for d in unique_dates:
            ts = pd.Timestamp(d)
            records.append(
                {
                    "full_date": d,
                    "year": ts.year,
                    "quarter": (ts.month - 1) // 3 + 1,
                    "month": ts.month,
                    "month_name": ts.strftime("%B"),
                    "week_number": int(ts.isocalendar()[1]),
                    "day_name": ts.strftime("%A"),
                    "is_weekend": ts.dayofweek >= 5,
                    "is_public_holiday": d.isoformat() in _PUBLIC_HOLIDAYS,
                }
            )
        df = pd.DataFrame(records)
        log.info("build_dim_date: %d date rows built", len(df))
        return df

    # ------------------------------------------------------------------
    # dim_product  (SCD Type 2)
    # ------------------------------------------------------------------

    def build_dim_product(self, df: pd.DataFrame) -> pd.DataFrame:
        """Deduplicate by product_sku; set SCD-2 defaults.

        Parameters
        ----------
        df:
            DataFrame with columns: product_sku, product_name, category_name.

        Returns
        -------
        pd.DataFrame
            Columns: product_sku, product_name, category_name,
            valid_from, valid_to, is_current.
        """
        if df.empty:
            return pd.DataFrame(
                columns=[
                    "product_sku",
                    "product_name",
                    "category_name",
                    "valid_from",
                    "valid_to",
                    "is_current",
                ]
            )
        today = date.today()
        cols = [
            c
            for c in ["product_sku", "product_name", "category_name"]
            if c in df.columns
        ]
        products = df[cols].drop_duplicates(subset=["product_sku"]).copy()
        if "product_name" in products.columns:
            products["product_name"] = products["product_name"].str.strip().str.title()
        if "category_name" not in products.columns:
            products["category_name"] = None
        products["valid_from"] = today
        products["valid_to"] = None
        products["is_current"] = True
        log.info("build_dim_product: %d product rows built", len(products))
        return products.reset_index(drop=True)

    # ------------------------------------------------------------------
    # dim_customer  (SCD Type 2)
    # ------------------------------------------------------------------

    def build_dim_customer(self, df: pd.DataFrame) -> pd.DataFrame:
        """Deduplicate by customer_id; set SCD-2 defaults.

        Parameters
        ----------
        df:
            DataFrame with columns: customer_id, and optionally
            customer_name / full_name, email.

        Returns
        -------
        pd.DataFrame
            Columns: customer_id, full_name, email,
            valid_from, valid_to, is_active.
        """
        if df.empty:
            return pd.DataFrame(
                columns=[
                    "customer_id",
                    "full_name",
                    "email",
                    "valid_from",
                    "valid_to",
                    "is_active",
                ]
            )
        today = date.today()
        cols = ["customer_id"]
        for col in ("customer_name", "full_name", "email"):
            if col in df.columns:
                cols.append(col)

        customers = df[cols].drop_duplicates(subset=["customer_id"]).copy()
        if (
            "customer_name" in customers.columns
            and "full_name" not in customers.columns
        ):
            customers = customers.rename(columns={"customer_name": "full_name"})
        if "full_name" not in customers.columns:
            customers["full_name"] = None
        if "email" not in customers.columns:
            customers["email"] = None
        customers["valid_from"] = today
        customers["valid_to"] = None
        customers["is_active"] = True
        log.info("build_dim_customer: %d customer rows built", len(customers))
        return customers.reset_index(drop=True)

    # ------------------------------------------------------------------
    # dim_store
    # ------------------------------------------------------------------

    def build_dim_store(self, df: pd.DataFrame) -> pd.DataFrame:
        """Deduplicate by store_id.

        Returns
        -------
        pd.DataFrame
            Columns: store_id, store_name, province.
        """
        if df.empty:
            return pd.DataFrame(columns=["store_id", "store_name", "province"])
        store_cols = [
            c for c in ["store_id", "store_name", "province"] if c in df.columns
        ]
        stores = df[store_cols].drop_duplicates(subset=["store_id"]).copy()
        if "province" not in stores.columns:
            stores["province"] = None
        log.info("build_dim_store: %d store rows built", len(stores))
        return stores.reset_index(drop=True)

    # ------------------------------------------------------------------
    # dim_geography
    # ------------------------------------------------------------------

    def build_dim_geography(self, df: pd.DataFrame) -> pd.DataFrame:
        """Deduplicate province + country combinations.

        If *df* has no ``country`` column, a default of ``"Ghana"`` is used.

        Returns
        -------
        pd.DataFrame
            Columns: province, country.
        """
        if df.empty or "province" not in df.columns:
            return pd.DataFrame(columns=["province", "country"])
        geo = df[["province"]].copy()
        if "country" in df.columns:
            geo["country"] = df["country"]
        else:
            geo["country"] = _COUNTRY_DEFAULT
        geo = geo.drop_duplicates(subset=["province", "country"])
        log.info("build_dim_geography: %d geography rows built", len(geo))
        return geo.reset_index(drop=True)

    # ------------------------------------------------------------------
    # cleanse_sales
    # ------------------------------------------------------------------

    def cleanse_sales(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardise column names and apply business rules.

        Rules applied
        -------------
        * Drop rows with null ``source_transaction_id`` or ``product_sku``.
        * Strip/title-case ``product_name``.
        * Clamp negative ``discount_applied`` to 0.
        * Recompute ``gross_amount = quantity * unit_price``.
        * Recompute ``net_amount = gross_amount - discount_applied``.
        """
        if df.empty:
            return df

        result = df.copy()

        # Drop rows lacking required keys
        required_nullcheck = [
            c for c in ("source_transaction_id", "product_sku") if c in result.columns
        ]
        if required_nullcheck:
            before = len(result)
            result = result.dropna(subset=required_nullcheck)
            dropped = before - len(result)
            if dropped:
                log.warning(
                    "cleanse_sales: dropped %d rows with null key columns", dropped
                )

        # Normalise product names
        if "product_name" in result.columns:
            result["product_name"] = result["product_name"].str.strip().str.title()

        # Clamp negative discounts
        if "discount_applied" in result.columns:
            result["discount_applied"] = (
                pd.to_numeric(result["discount_applied"], errors="coerce")
                .fillna(0)
                .clip(lower=0)
            )

        # Recompute amounts
        if "quantity" in result.columns and "unit_price" in result.columns:
            qty = pd.to_numeric(result["quantity"], errors="coerce").fillna(0)
            price = pd.to_numeric(result["unit_price"], errors="coerce").fillna(0)
            result["gross_amount"] = qty * price
            discount = pd.to_numeric(
                result.get("discount_applied", pd.Series(0, index=result.index)),
                errors="coerce",
            ).fillna(0)
            result["net_amount"] = result["gross_amount"] - discount

        log.info("cleanse_sales: %d rows after cleansing", len(result))
        return result.reset_index(drop=True)
