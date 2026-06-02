"""Tests for etl.transform — Transformer dimension-building and cleansing."""

from datetime import date

import pandas as pd
import pytest
from etl.transform import Transformer

# ---------------------------------------------------------------------------
# dimDate
# ---------------------------------------------------------------------------


def test_build_dim_date_columns(transformer: Transformer) -> None:
    """build_dim_date for a single date must return the required schema columns."""
    df = transformer.build_dim_date([date(2024, 1, 15)])
    required = {
        "fullDate",
        "year",
        "quarter",
        "month",
        "monthName",
        "weekNumber",
        "dayName",
        "isWeekend",
        "isPublicHoliday",
    }
    missing = required - set(df.columns)
    assert not missing, f"dimDate is missing columns: {missing}"
    assert len(df) == 1


def test_build_dim_date_weekend(transformer: Transformer) -> None:
    """A Saturday must produce isWeekend=True."""
    # 2024-01-06 is a Saturday
    df = transformer.build_dim_date([date(2024, 1, 6)])
    assert bool(df.loc[0, "isWeekend"]) is True


def test_build_dim_date_weekday(transformer: Transformer) -> None:
    """A Monday must produce isWeekend=False."""
    # 2024-01-08 is a Monday
    df = transformer.build_dim_date([date(2024, 1, 8)])
    assert bool(df.loc[0, "isWeekend"]) is False


# ---------------------------------------------------------------------------
# dimProduct
# ---------------------------------------------------------------------------


def test_build_dim_product_deduplication(
    transformer: Transformer, sample_sales_df: pd.DataFrame
) -> None:
    """Duplicate SKU rows must collapse into one product row per unique SKU."""
    # sample_sales_df has SKU-A appearing twice (rows 0 and 3)
    df = transformer.build_dim_product(sample_sales_df)
    unique_skus = sample_sales_df["productSKU"].nunique()
    assert len(df) == unique_skus, f"Expected {unique_skus} product rows, got {len(df)}"


# ---------------------------------------------------------------------------
# dimCustomer
# ---------------------------------------------------------------------------


def test_build_dim_customer_sets_scd_fields(
    transformer: Transformer, sample_sales_df: pd.DataFrame
) -> None:
    """build_dim_customer must include an isActive column."""
    df = transformer.build_dim_customer(sample_sales_df)
    assert "isActive" in df.columns, "dimCustomer must contain isActive"
    assert df["isActive"].all(), "All newly built customer records should be active"


# ---------------------------------------------------------------------------
# cleanse_sales
# ---------------------------------------------------------------------------


def test_cleanse_sales_drops_null_sku(
    transformer: Transformer, sample_sales_df: pd.DataFrame
) -> None:
    """A row with productSKU=None must be dropped during cleansing."""
    df = sample_sales_df.copy()
    # Append a row with a null productSKU
    null_row = df.iloc[0].copy()
    null_row["productSKU"] = None
    df = pd.concat([df, null_row.to_frame().T], ignore_index=True)
    cleansed = transformer.cleanse_sales(df)
    assert cleansed["productSKU"].notna().all(), "Null-SKU rows must be dropped"
    assert len(cleansed) == len(
        sample_sales_df
    ), "Only the null-SKU row should be removed"


def test_cleanse_sales_clamps_negative_discount(
    transformer: Transformer, sample_sales_df: pd.DataFrame
) -> None:
    """A negative discountApplied must be clamped to 0 after cleansing."""
    df = sample_sales_df.copy()
    df.loc[0, "discountApplied"] = -10.0
    cleansed = transformer.cleanse_sales(df)
    assert (
        cleansed.loc[0, "discountApplied"] == 0.0
    ), "Negative discount must be clamped to 0"


def test_cleanse_sales_recomputes_net_amount(
    transformer: Transformer, sample_sales_df: pd.DataFrame
) -> None:
    """netAmount must equal grossAmount - discountApplied after cleansing."""
    df = sample_sales_df.copy()
    # Fix values so the recomputed result is predictable
    df.loc[0, "discountApplied"] = 10.0
    df.loc[0, "quantity"] = 2
    df.loc[0, "unitPrice"] = 50.0
    cleansed = transformer.cleanse_sales(df)
    expected_net = cleansed.loc[0, "grossAmount"] - cleansed.loc[0, "discountApplied"]
    assert cleansed.loc[0, "netAmount"] == pytest.approx(
        expected_net
    ), "netAmount must equal grossAmount - discountApplied"
