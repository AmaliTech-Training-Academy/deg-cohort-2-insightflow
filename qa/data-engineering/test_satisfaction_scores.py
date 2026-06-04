"""
Tests for regional satisfaction scoring logic (US-14).

Covers:
- Satisfaction mean: average of productRating + deliveryRating (scale 1-5)
- NPS formula: (promoters - detractors) / total * 100
- 3.5 threshold highlight logic
"""

import pytest

SATISFACTION_THRESHOLD = 3.5


# ---------------------------------------------------------------------------
# Pure-Python equivalents of the SQL view logic
# ---------------------------------------------------------------------------


def compute_satisfaction(rows):
    """
    Mean satisfaction = (AVG(productRating) + AVG(deliveryRating)) / 2
    Mirrors the SQL: (AVG("productRating") + AVG("deliveryRating")) / 2.0
    """
    if not rows:
        return None
    avg_product = sum(r["product_rating"] for r in rows) / len(rows)
    avg_delivery = sum(r["delivery_rating"] for r in rows) / len(rows)
    return round((avg_product + avg_delivery) / 2.0, 2)


def compute_nps(rows):
    """
    NPS = (promoters - detractors) / total * 100
    promoters : npsScore >= 9
    detractors: npsScore <= 6
    passives  : npsScore 7-8
    """
    if not rows:
        return None
    total = len(rows)
    promoters = sum(1 for r in rows if r["nps_score"] >= 9)
    detractors = sum(1 for r in rows if r["nps_score"] <= 6)
    return round((promoters - detractors) / total * 100, 1)


def is_below_threshold(avg_satisfaction, threshold=SATISFACTION_THRESHOLD):
    """Return True when a region should be highlighted."""
    if avg_satisfaction is None:
        return False
    return avg_satisfaction < threshold


def regional_satisfaction_summary(regions):
    """
    Aggregate per-region feedback into summary rows.
    regions: dict mapping region_name -> list of feedback dicts.
    Returns list of summary dicts sorted by avg_satisfaction DESC.
    """
    results = []
    for region_name, rows in regions.items():
        avg_sat = compute_satisfaction(rows)
        nps = compute_nps(rows)
        results.append(
            {
                "region_name": region_name,
                "feedback_count": len(rows),
                "avg_satisfaction": avg_sat,
                "nps_score": nps,
                "promoters": sum(1 for r in rows if r["nps_score"] >= 9),
                "detractors": sum(1 for r in rows if r["nps_score"] <= 6),
                "passives": sum(
                    1 for r in rows if 7 <= r["nps_score"] <= 8
                ),
                "below_threshold": is_below_threshold(avg_sat),
            }
        )
    return sorted(
        results,
        key=lambda r: (r["avg_satisfaction"] or 0),
        reverse=True,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _row(product_rating, delivery_rating, nps_score):
    return {
        "product_rating": product_rating,
        "delivery_rating": delivery_rating,
        "nps_score": nps_score,
    }


@pytest.fixture
def high_satisfaction_rows():
    return [_row(5, 5, 10), _row(4, 5, 9), _row(5, 4, 10)]


@pytest.fixture
def low_satisfaction_rows():
    return [_row(2, 3, 4), _row(3, 2, 5), _row(2, 2, 3)]


@pytest.fixture
def borderline_rows():
    """Average lands exactly at 3.5 — should NOT be flagged."""
    return [_row(3, 4, 7), _row(4, 3, 8)]  # avg = (3.5 + 3.5) / 2 = 3.5


@pytest.fixture
def mixed_nps_rows():
    return [
        _row(4, 4, 10),  # promoter
        _row(4, 4, 9),   # promoter
        _row(3, 3, 7),   # passive
        _row(3, 3, 8),   # passive
        _row(2, 2, 5),   # detractor
        _row(2, 2, 4),   # detractor
        _row(2, 2, 3),   # detractor
    ]


# ---------------------------------------------------------------------------
# Satisfaction mean tests
# ---------------------------------------------------------------------------


class TestSatisfactionMean:
    def test_perfect_scores(self, high_satisfaction_rows):
        result = compute_satisfaction(high_satisfaction_rows)
        assert result == round(
            ((5 + 4 + 5) / 3 + (5 + 5 + 4) / 3) / 2, 2
        )

    def test_low_scores(self, low_satisfaction_rows):
        result = compute_satisfaction(low_satisfaction_rows)
        assert result < SATISFACTION_THRESHOLD

    def test_mean_is_average_of_both_ratings(self):
        rows = [_row(4, 2, 7)]  # avg_product=4, avg_delivery=2 → (4+2)/2=3.0
        assert compute_satisfaction(rows) == 3.0

    def test_empty_rows_returns_none(self):
        assert compute_satisfaction([]) is None

    def test_single_row(self):
        rows = [_row(5, 3, 9)]
        assert compute_satisfaction(rows) == 4.0

    def test_all_ratings_equal(self):
        rows = [_row(3, 3, 7), _row(3, 3, 8)]
        assert compute_satisfaction(rows) == 3.0


# ---------------------------------------------------------------------------
# NPS formula tests
# ---------------------------------------------------------------------------


class TestNPSFormula:
    def test_all_promoters(self):
        rows = [_row(5, 5, 10), _row(5, 5, 9), _row(5, 5, 9)]
        assert compute_nps(rows) == 100.0

    def test_all_detractors(self):
        rows = [_row(2, 2, 3), _row(2, 2, 5), _row(2, 2, 6)]
        assert compute_nps(rows) == -100.0

    def test_equal_promoters_and_detractors(self, mixed_nps_rows):
        # 2 promoters, 3 detractors, 2 passives → (2-3)/7*100 ≈ -14.3
        result = compute_nps(mixed_nps_rows)
        assert result == round((2 - 3) / 7 * 100, 1)

    def test_passives_do_not_count(self):
        rows = [_row(4, 4, 7), _row(4, 4, 8)]  # all passives
        assert compute_nps(rows) == 0.0

    def test_nps_range_is_minus100_to_100(self, mixed_nps_rows):
        result = compute_nps(mixed_nps_rows)
        assert -100.0 <= result <= 100.0

    def test_empty_returns_none(self):
        assert compute_nps([]) is None

    def test_promoter_threshold_is_9(self):
        assert _row(5, 5, 9)["nps_score"] >= 9   # promoter
        assert _row(5, 5, 8)["nps_score"] not in range(9, 11)  # passive

    def test_detractor_threshold_is_6(self):
        assert _row(2, 2, 6)["nps_score"] <= 6   # detractor
        assert _row(2, 2, 7)["nps_score"] > 6    # passive


# ---------------------------------------------------------------------------
# Threshold / highlight tests
# ---------------------------------------------------------------------------


class TestThresholdHighlight:
    def test_below_threshold_flagged(self, low_satisfaction_rows):
        avg = compute_satisfaction(low_satisfaction_rows)
        assert is_below_threshold(avg) is True

    def test_above_threshold_not_flagged(self, high_satisfaction_rows):
        avg = compute_satisfaction(high_satisfaction_rows)
        assert is_below_threshold(avg) is False

    def test_exactly_35_not_flagged(self, borderline_rows):
        avg = compute_satisfaction(borderline_rows)
        assert avg == 3.5
        assert is_below_threshold(avg) is False  # < 3.5, not <=

    def test_just_below_threshold_flagged(self):
        rows = [_row(3, 3, 6), _row(3, 4, 5)]  # avg = (3+3.5)/2 = 3.25
        avg = compute_satisfaction(rows)
        assert avg < SATISFACTION_THRESHOLD
        assert is_below_threshold(avg) is True

    def test_none_satisfaction_not_flagged(self):
        assert is_below_threshold(None) is False


# ---------------------------------------------------------------------------
# Regional summary integration tests
# ---------------------------------------------------------------------------


class TestRegionalSummary:
    def test_sorted_by_satisfaction_descending(self):
        regions = {
            "Kigali": [_row(5, 5, 10), _row(4, 5, 9)],
            "Eastern": [_row(2, 2, 3), _row(3, 2, 4)],
            "Northern": [_row(3, 4, 7), _row(4, 3, 8)],
        }
        result = regional_satisfaction_summary(regions)
        scores = [r["avg_satisfaction"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_below_threshold_regions_flagged_correctly(self):
        regions = {
            "Kigali": [_row(5, 5, 10)],   # high
            "Eastern": [_row(2, 2, 4)],   # low
        }
        result = {r["region_name"]: r for r in regional_satisfaction_summary(regions)}
        assert result["Kigali"]["below_threshold"] is False
        assert result["Eastern"]["below_threshold"] is True

    def test_nps_computed_per_region(self):
        regions = {
            "Kigali": [_row(5, 5, 10), _row(5, 5, 9)],  # NPS = 100
            "Eastern": [_row(2, 2, 3), _row(2, 2, 5)],  # NPS = -100
        }
        result = {r["region_name"]: r for r in regional_satisfaction_summary(regions)}
        assert result["Kigali"]["nps_score"] == 100.0
        assert result["Eastern"]["nps_score"] == -100.0

    def test_feedback_count_correct(self):
        regions = {"Kigali": [_row(4, 4, 9)] * 5}
        result = regional_satisfaction_summary(regions)
        assert result[0]["feedback_count"] == 5
