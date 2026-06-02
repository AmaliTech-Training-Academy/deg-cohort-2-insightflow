"""Tests for etl.quality — DataQualityChecker, QualityScore, QUALITY_THRESHOLDS."""

import pandas as pd
from etl.quality import QUALITY_THRESHOLDS, DataQualityChecker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sales_checks(checker: DataQualityChecker):
    """Return the standard check list for a sales DataFrame."""
    return [
        (
            "null_keys",
            lambda df: checker.check_null_keys(df, ["product_sku", "customer_id"]),
        ),
        ("positive_quantity", checker.check_positive_quantities),
        ("positive_price", checker.check_positive_prices),
        (
            "discount_range",
            lambda df: checker.check_discount_range(df, "discount_applied"),
        ),
    ]


def _feedback_checks(checker: DataQualityChecker):
    """Return the standard check list for a feedback DataFrame."""
    return [
        (
            "satisfaction_score_range",
            lambda df: checker.check_score_range(df, "satisfaction_score", 1, 10),
        ),
        (
            "nps_score_range",
            lambda df: checker.check_score_range(df, "nps_score", 0, 10),
        ),
    ]


# ---------------------------------------------------------------------------
# Null-key checks
# ---------------------------------------------------------------------------


def test_null_key_check_passes_clean_data(
    quality_checker: DataQualityChecker, sample_sales_df: pd.DataFrame
) -> None:
    """All five clean rows must pass the null-key check."""
    result = quality_checker.check_null_keys(
        sample_sales_df, ["product_sku", "customer_id"]
    )
    assert result.all(), "Expected all rows to pass null-key check on clean data"


def test_null_key_check_fails_on_null_sku(
    quality_checker: DataQualityChecker, sample_sales_df: pd.DataFrame
) -> None:
    """A row with product_sku=None must fail the null-key check."""
    df = sample_sales_df.copy()
    df.loc[0, "product_sku"] = None
    result = quality_checker.check_null_keys(df, ["product_sku", "customer_id"])
    assert not result.iloc[0], "Row with null product_sku should fail null-key check"
    assert result.iloc[1:].all(), "Unmodified rows should still pass"


# ---------------------------------------------------------------------------
# Quantity / price checks
# ---------------------------------------------------------------------------


def test_positive_quantity_check(
    quality_checker: DataQualityChecker, sample_sales_df: pd.DataFrame
) -> None:
    """A row with quantity=-1 must fail the positive-quantity check."""
    df = sample_sales_df.copy()
    df.loc[2, "quantity"] = -1
    result = quality_checker.check_positive_quantities(df)
    assert not result.iloc[2], "Negative quantity should fail"
    assert result.drop(index=2).all(), "Other rows should pass"


def test_positive_price_check(
    quality_checker: DataQualityChecker, sample_sales_df: pd.DataFrame
) -> None:
    """A row with unit_price=0 must fail the positive-price check."""
    df = sample_sales_df.copy()
    df.loc[1, "unit_price"] = 0
    result = quality_checker.check_positive_prices(df)
    assert not result.iloc[1], "Zero unit_price should fail"
    assert result.drop(index=1).all(), "Other rows should pass"


# ---------------------------------------------------------------------------
# Discount range check
# ---------------------------------------------------------------------------


def test_discount_range_check(
    quality_checker: DataQualityChecker, sample_sales_df: pd.DataFrame
) -> None:
    """A row where discount > unit_price must fail the discount-range check."""
    df = sample_sales_df.copy()
    # Set discount far above unit_price on row 0
    df.loc[0, "discount_applied"] = df.loc[0, "unit_price"] + 100
    result = quality_checker.check_discount_range(df, "discount_applied")
    assert not result.iloc[0], "Discount exceeding unit_price should fail"
    assert result.iloc[1:].all(), "Clean rows should pass"


# ---------------------------------------------------------------------------
# Score-range check (feedback)
# ---------------------------------------------------------------------------


def test_score_range_check_feedback(
    quality_checker: DataQualityChecker, sample_feedback_df: pd.DataFrame
) -> None:
    """A satisfaction_score of 11 (out of 1–10) must fail the score-range check."""
    df = sample_feedback_df.copy()
    df.loc[0, "satisfaction_score"] = 11
    result = quality_checker.check_score_range(df, "satisfaction_score", 1, 10)
    assert not result.iloc[0], "Score 11 should fail range check [1, 10]"
    assert result.iloc[1:].all(), "Valid scores should pass"


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------


def test_overall_quality_score_clean(
    quality_checker: DataQualityChecker, sample_sales_df: pd.DataFrame
) -> None:
    """All-clean data must produce an overall_score >= 0.9."""
    checks = _sales_checks(quality_checker)
    _, summary = quality_checker.score_dataframe(sample_sales_df, "fact_sales", checks)
    assert (
        summary["overall_score"] >= 0.9
    ), f"Expected score >=0.9 on clean data, got {summary['overall_score']}"


def test_quality_score_degraded(
    quality_checker: DataQualityChecker, sample_sales_df: pd.DataFrame
) -> None:
    """Corrupting 3 of 5 rows must push overall_score below 0.9."""
    df = sample_sales_df.copy()
    df.loc[0, "product_sku"] = None  # fails null-key check
    df.loc[1, "quantity"] = -5  # fails positive-quantity check
    df.loc[2, "unit_price"] = 0  # fails positive-price check
    checks = _sales_checks(quality_checker)
    _, summary = quality_checker.score_dataframe(df, "fact_sales", checks)
    assert (
        summary["overall_score"] < 0.9
    ), f"Expected score <0.9 with 3 corrupt rows, got {summary['overall_score']}"


# ---------------------------------------------------------------------------
# Thresholds constant
# ---------------------------------------------------------------------------


def test_quality_thresholds_defined() -> None:
    """QUALITY_THRESHOLDS must include keys for all three fact tables."""
    required = {"fact_sales", "fact_feedback", "fact_inventory_snapshot"}
    missing = required - set(QUALITY_THRESHOLDS.keys())
    assert not missing, f"QUALITY_THRESHOLDS missing keys: {missing}"
