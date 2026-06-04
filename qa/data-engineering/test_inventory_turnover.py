
import pytest

DEFAULT_THRESHOLD = 2.0


# ---------------------------------------------------------------------------
# Pure-Python equivalents of the SQL view logic
# ---------------------------------------------------------------------------


def compute_turnover(units_sold, avg_inventory):
    """
    turnover = units_sold / avg_inventory_level
    Returns None when avg_inventory is 0 or None (mirrors SQL NULLIF).
    """
    if not avg_inventory:
        return None
    return round(units_sold / avg_inventory, 2)


def is_below_threshold(turnover_ratio, threshold=DEFAULT_THRESHOLD):
    """Return True when a category should be flagged."""
    if turnover_ratio is None:
        return False
    return turnover_ratio < threshold


def category_turnover_summary(categories, threshold=DEFAULT_THRESHOLD):
    """
    Aggregate per-category sales and inventory into a summary.

    Args:
        categories: dict mapping category_name ->
                    {"units_sold": int, "avg_inventory": float}
        threshold: flag categories below this turnover ratio

    Returns:
        List of summary dicts sorted by turnover_ratio ASC (lowest first).
    """
    results = []
    for name, data in categories.items():
        ratio = compute_turnover(data["units_sold"], data["avg_inventory"])
        results.append(
            {
                "category": name,
                "units_sold": data["units_sold"],
                "avg_inventory": data["avg_inventory"],
                "turnover_ratio": ratio,
                "threshold": threshold,
                "below_threshold": is_below_threshold(ratio, threshold),
            }
        )
    return sorted(
        results,
        key=lambda r: (r["turnover_ratio"] is None, r["turnover_ratio"] or 0),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def healthy_categories():
    return {
        "Electronics": {"units_sold": 500, "avg_inventory": 100},   # 5.0
        "Clothing": {"units_sold": 300, "avg_inventory": 100},      # 3.0
        "Food": {"units_sold": 800, "avg_inventory": 200},          # 4.0
    }


@pytest.fixture
def mixed_categories():
    return {
        "Electronics": {"units_sold": 500, "avg_inventory": 100},  # 5.0 OK
        "Clothing": {"units_sold": 100, "avg_inventory": 200},     # 0.5 LOW
        "Food": {"units_sold": 200, "avg_inventory": 100},         # 2.0 edge
        "Furniture": {"units_sold": 50, "avg_inventory": 500},     # 0.1 LOW
    }


# ---------------------------------------------------------------------------
# Turnover calculation tests
# ---------------------------------------------------------------------------


class TestTurnoverCalculation:
    def test_basic_formula(self):
        assert compute_turnover(500, 100) == 5.0

    def test_fractional_result(self):
        assert compute_turnover(100, 300) == round(100 / 300, 2)

    def test_zero_inventory_returns_none(self):
        assert compute_turnover(500, 0) is None

    def test_none_inventory_returns_none(self):
        assert compute_turnover(500, None) is None

    def test_zero_sales(self):
        assert compute_turnover(0, 100) == 0.0

    def test_result_rounded_to_two_decimals(self):
        result = compute_turnover(1, 3)  # 0.333...
        assert result == 0.33

    def test_high_turnover(self):
        assert compute_turnover(1000, 10) == 100.0

    def test_units_equal_inventory(self):
        assert compute_turnover(200, 200) == 1.0


# ---------------------------------------------------------------------------
# Threshold flag tests
# ---------------------------------------------------------------------------


class TestThresholdFlag:
    def test_below_default_threshold_flagged(self):
        assert is_below_threshold(1.5) is True

    def test_above_default_threshold_not_flagged(self):
        assert is_below_threshold(2.5) is False

    def test_exactly_at_threshold_not_flagged(self):
        # threshold is strict less-than (<), so 2.0 is NOT flagged
        assert is_below_threshold(2.0) is False

    def test_just_below_threshold_flagged(self):
        assert is_below_threshold(1.99) is True

    def test_none_ratio_not_flagged(self):
        assert is_below_threshold(None) is False

    def test_custom_threshold(self):
        assert is_below_threshold(3.0, threshold=4.0) is True
        assert is_below_threshold(5.0, threshold=4.0) is False

    def test_zero_turnover_always_flagged(self):
        assert is_below_threshold(0.0) is True

    def test_very_high_custom_threshold(self):
        assert is_below_threshold(10.0, threshold=15.0) is True


# ---------------------------------------------------------------------------
# Category summary integration tests
# ---------------------------------------------------------------------------


class TestCategorySummary:
    def test_sorted_by_turnover_ascending(self, mixed_categories):
        result = category_turnover_summary(mixed_categories)
        ratios = [r["turnover_ratio"] for r in result]
        valid = [r for r in ratios if r is not None]
        assert valid == sorted(valid)

    def test_below_threshold_categories_flagged(self, mixed_categories):
        result = {
            r["category"]: r
            for r in category_turnover_summary(mixed_categories)
        }
        assert result["Electronics"]["below_threshold"] is False  # 5.0
        assert result["Clothing"]["below_threshold"] is True      # 0.5
        assert result["Furniture"]["below_threshold"] is True     # 0.1

    def test_exact_threshold_boundary_not_flagged(self, mixed_categories):
        # Food: 200/100 = 2.0 == threshold → NOT flagged
        result = {
            r["category"]: r
            for r in category_turnover_summary(mixed_categories)
        }
        assert result["Food"]["below_threshold"] is False

    def test_all_healthy_none_flagged(self, healthy_categories):
        result = category_turnover_summary(healthy_categories)
        assert all(not r["below_threshold"] for r in result)

    def test_threshold_stored_in_each_row(self, healthy_categories):
        result = category_turnover_summary(healthy_categories, threshold=3.0)
        assert all(r["threshold"] == 3.0 for r in result)

    def test_custom_threshold_changes_flags(self, healthy_categories):
        # With threshold=6.0 all three categories should be flagged
        result = category_turnover_summary(healthy_categories, threshold=6.0)
        assert all(r["below_threshold"] for r in result)

    def test_required_columns_present(self, healthy_categories):
        result = category_turnover_summary(healthy_categories)
        for row in result:
            for col in (
                "category",
                "units_sold",
                "avg_inventory",
                "turnover_ratio",
                "threshold",
                "below_threshold",
            ):
                assert col in row

    def test_zero_inventory_category_handled(self):
        categories = {
            "Ghost": {"units_sold": 100, "avg_inventory": 0},
        }
        result = category_turnover_summary(categories)
        assert result[0]["turnover_ratio"] is None
        assert result[0]["below_threshold"] is False
