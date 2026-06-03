"""Transformation module for the InsightFlow ETL pipeline.

Builds dimension and fact DataFrames from cleansed OLTP extracts.
All methods operate purely on pandas DataFrames — no database I/O.
"""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd

log = logging.getLogger("insightflow.transform")

_COUNTRY_DEFAULT = "Rwanda"

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
    # dimDate
    # ------------------------------------------------------------------

    def build_dim_date(self, dates: list[date]) -> pd.DataFrame:
        """Generate dimDate rows for each unique date in *dates*.

        Parameters
        ----------
        dates:
            Collection of :class:`datetime.date` objects (duplicates OK).

        Returns
        -------
        pd.DataFrame
            Columns: fullDate, year, quarter, month, monthName,
            weekNumber, dayName, isWeekend, isPublicHoliday.
        """
        unique_dates = sorted(set(d for d in dates if d is not None))
        records = []
        for d in unique_dates:
            ts = pd.Timestamp(d)
            records.append(
                {
                    "fullDate": d,
                    "year": ts.year,
                    "quarter": (ts.month - 1) // 3 + 1,
                    "month": ts.month,
                    "monthName": ts.strftime("%B"),
                    "weekNumber": int(ts.isocalendar()[1]),
                    "dayName": ts.strftime("%A"),
                    "isWeekend": ts.dayofweek >= 5,
                    "isPublicHoliday": d.isoformat() in _PUBLIC_HOLIDAYS,
                }
            )
        df = pd.DataFrame(records)
        log.info("build_dim_date: %d date rows built", len(df))
        return df

    # ------------------------------------------------------------------
    # dimProduct  (SCD Type 2)
    # ------------------------------------------------------------------

    def build_dim_product(self, df: pd.DataFrame) -> pd.DataFrame:
        """Deduplicate by productSKU; set SCD-2 defaults.

        Parameters
        ----------
        df:
            DataFrame with columns: productSKU, productName, categoryName.

        Returns
        -------
        pd.DataFrame
            Columns: productSKU, productName, categoryName,
            validFrom, validTo, isCurrent.
        """
        if df.empty:
            return pd.DataFrame(
                columns=[
                    "productSKU",
                    "productName",
                    "categoryName",
                    "validFrom",
                    "validTo",
                    "isCurrent",
                ]
            )
        today = date.today()
        cols = [
            c for c in ["productSKU", "productName", "categoryName"] if c in df.columns
        ]
        products = df[cols].drop_duplicates(subset=["productSKU"]).copy()
        if "productName" in products.columns:
            products["productName"] = products["productName"].str.strip().str.title()
        if "categoryName" not in products.columns:
            products["categoryName"] = None
        products["validFrom"] = today
        products["validTo"] = None
        products["isCurrent"] = True
        log.info("build_dim_product: %d product rows built", len(products))
        return products.reset_index(drop=True)

    # ------------------------------------------------------------------
    # dimCustomer  (SCD Type 2)
    # ------------------------------------------------------------------

    def build_dim_customer(self, df: pd.DataFrame) -> pd.DataFrame:
        """Deduplicate by customerId; set SCD-2 defaults.

        Parameters
        ----------
        df:
            DataFrame with columns: customerId, and optionally
            customerName / fullName, email.

        Returns
        -------
        pd.DataFrame
            Columns: customerId, fullName, email,
            validFrom, validTo, isActive.
        """
        if df.empty:
            return pd.DataFrame(
                columns=[
                    "customerId",
                    "fullName",
                    "email",
                    "validFrom",
                    "validTo",
                    "isActive",
                ]
            )
        today = date.today()
        cols = ["customerId"]
        for col in ("customerName", "fullName", "email"):
            if col in df.columns:
                cols.append(col)

        customers = df[cols].drop_duplicates(subset=["customerId"]).copy()
        if "customerName" in customers.columns and "fullName" not in customers.columns:
            customers = customers.rename(columns={"customerName": "fullName"})
        if "fullName" not in customers.columns:
            customers["fullName"] = None
        if "email" not in customers.columns:
            customers["email"] = None
        customers["validFrom"] = today
        customers["validTo"] = None
        customers["isActive"] = True
        log.info("build_dim_customer: %d customer rows built", len(customers))
        return customers.reset_index(drop=True)

    # ------------------------------------------------------------------
    # dimStore
    # ------------------------------------------------------------------

    def build_dim_store(self, df: pd.DataFrame) -> pd.DataFrame:
        """Deduplicate by storeId.

        Returns
        -------
        pd.DataFrame
            Columns: storeId, storeName, province.
        """
        if df.empty:
            return pd.DataFrame(columns=["storeId", "storeName", "province"])
        store_cols = [
            c for c in ["storeId", "storeName", "province"] if c in df.columns
        ]
        stores = df[store_cols].drop_duplicates(subset=["storeId"]).copy()
        if "province" not in stores.columns:
            stores["province"] = None
        log.info("build_dim_store: %d store rows built", len(stores))
        return stores.reset_index(drop=True)

    # ------------------------------------------------------------------
    # dimGeography
    # ------------------------------------------------------------------

    def build_dim_geography(self, df: pd.DataFrame) -> pd.DataFrame:
        """Deduplicate province + country combinations.

        If *df* has no ``country`` column, a default of ``"Rwanda"`` is used.

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
        * Drop rows with null ``sourceTransactionId`` or ``productSKU``.
        * Strip/title-case ``productName``.
        * Clamp negative ``discountApplied`` to 0.
        * Recompute ``grossAmount = quantity * unitPrice``.
        * Recompute ``netAmount = grossAmount - discountApplied``.
        """
        if df.empty:
            return df

        result = df.copy()

        # Drop rows lacking required keys
        required_nullcheck = [
            c for c in ("sourceTransactionId", "productSKU") if c in result.columns
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
        if "productName" in result.columns:
            result["productName"] = result["productName"].str.strip().str.title()

        # Clamp negative discounts
        if "discountApplied" in result.columns:
            result["discountApplied"] = (
                pd.to_numeric(result["discountApplied"], errors="coerce")
                .fillna(0)
                .clip(lower=0)
            )

        # Recompute amounts
        if "quantity" in result.columns and "unitPrice" in result.columns:
            qty = pd.to_numeric(result["quantity"], errors="coerce").fillna(0)
            price = pd.to_numeric(result["unitPrice"], errors="coerce").fillna(0)
            result["grossAmount"] = qty * price
            discount = pd.to_numeric(
                result.get("discountApplied", pd.Series(0, index=result.index)),
                errors="coerce",
            ).fillna(0)
            result["netAmount"] = result["grossAmount"] - discount

        log.info("cleanse_sales: %d rows after cleansing", len(result))
        return result.reset_index(drop=True)
