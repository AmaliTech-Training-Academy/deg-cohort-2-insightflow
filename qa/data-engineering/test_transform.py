"""Tests for etl.transform — Transformer dimension-building and cleansing."""

from datetime import date

import pandas as pd
import pytest
from etl.transform import Transformer

# ---------------------------------------------------------------------------
# dim_date
# ---------------------------------------------------------------------------


def test_build_dim_date_columns(transformer: Transformer) -> None:
    """build_dim_date for a single date must return the required schema columns."""
    df = transformer.build_dim_date([date(2024, 1, 15)])
    required = {
        "full_date",
        "year",
        "quarter",
        "month",
        "month_name",
        "week_number",
        "day_name",
        "is_weekend",
        "is_public_holiday",
    }
    missing = required - set(df.columns)
    assert not missing, f"dim_date is missing columns: {missing}"
    assert len(df) == 1


def test_build_dim_date_weekend(transformer: Transformer) -> None:
    """A Saturday must produce is_weekend=True."""
    # 2024-01-06 is a Saturday
    df = transformer.build_dim_date([date(2024, 1, 6)])
    assert bool(df.loc[0, "is_weekend"]) is True


def test_build_dim_date_weekday(transformer: Transformer) -> None:
    """A Monday must produce is_weekend=False."""
    # 2024-01-08 is a Monday
    df = transformer.build_dim_date([date(2024, 1, 8)])
    assert bool(df.loc[0, "is_weekend"]) is False


# ---------------------------------------------------------------------------
# dim_product
# ---------------------------------------------------------------------------


def test_build_dim_product_deduplication(
    transformer: Transformer, sample_sales_df: pd.DataFrame
) -> None:
    """Duplicate SKU rows must collapse into one product row per unique SKU."""
    # sample_sales_df has SKU-A appearing twice (rows 0 and 3)
    df = transformer.build_dim_product(sample_sales_df)
    unique_skus = sample_sales_df["product_sku"].nunique()
    assert len(df) == unique_skus, f"Expected {unique_skus} product rows, got {len(df)}"


# ---------------------------------------------------------------------------
# dim_customer
# ---------------------------------------------------------------------------


def test_build_dim_customer_sets_scd_fields(
    transformer: Transformer, sample_sales_df: pd.DataFrame
) -> None:
    """build_dim_customer must include an is_active column."""
    df = transformer.build_dim_customer(sample_sales_df)
    assert "is_active" in df.columns, "dim_customer must contain is_active"
    assert df["is_active"].all(), "All newly built customer records should be active"


# ---------------------------------------------------------------------------
# cleanse_sales
# ---------------------------------------------------------------------------


def test_cleanse_sales_drops_null_sku(
    transformer: Transformer, sample_sales_df: pd.DataFrame
) -> None:
    """A row with product_sku=None must be dropped during cleansing."""
    df = sample_sales_df.copy()
    # Append a row with a null product_sku
    null_row = df.iloc[0].copy()
    null_row["product_sku"] = None
    df = pd.concat([df, null_row.to_frame().T], ignore_index=True)
    cleansed = transformer.cleanse_sales(df)
    assert cleansed["product_sku"].notna().all(), "Null-SKU rows must be dropped"
    assert len(cleansed) == len(
        sample_sales_df
    ), "Only the null-SKU row should be removed"


def test_cleanse_sales_clamps_negative_discount(
    transformer: Transformer, sample_sales_df: pd.DataFrame
) -> None:
    """A negative discount_applied must be clamped to 0 after cleansing."""
    df = sample_sales_df.copy()
    df.loc[0, "discount_applied"] = -10.0
    cleansed = transformer.cleanse_sales(df)
    assert (
        cleansed.loc[0, "discount_applied"] == 0.0
    ), "Negative discount must be clamped to 0"


def test_cleanse_sales_recomputes_net_amount(
    transformer: Transformer, sample_sales_df: pd.DataFrame
) -> None:
    """net_amount must equal gross_amount - discount_applied after cleansing."""
    df = sample_sales_df.copy()
    # Fix values so the recomputed result is predictable
    df.loc[0, "discount_applied"] = 10.0
    df.loc[0, "quantity"] = 2
    df.loc[0, "unit_price"] = 50.0
    cleansed = transformer.cleanse_sales(df)
    expected_net = cleansed.loc[0, "gross_amount"] - cleansed.loc[0, "discount_applied"]
    assert cleansed.loc[0, "net_amount"] == pytest.approx(
        expected_net
    ), "net_amount must equal gross_amount - discount_applied"
