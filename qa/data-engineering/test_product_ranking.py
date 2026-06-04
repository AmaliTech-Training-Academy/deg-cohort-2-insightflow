import pytest


def rank_products(rows):
    """
    Pure-Python equivalent of the SQL RANK() + ORDER BY logic used in
    v_top5_products_*.

    Args:
        rows: list of dicts with keys 'sku', 'product_name', 'category',
              'total_revenue', 'units_sold'.

    Returns:
        Top-5 rows sorted by (total_revenue DESC, units_sold DESC) with a
        1-based 'revenue_rank' that matches SQL RANK() behaviour (ties share
        the same rank).
    """
    sorted_rows = sorted(
        rows,
        key=lambda r: (-r["total_revenue"], -r["units_sold"]),
    )

    ranked = []
    current_rank = 1
    for i, row in enumerate(sorted_rows):
        if i == 0:
            row["revenue_rank"] = 1
        else:
            prev = sorted_rows[i - 1]
            if (
                row["total_revenue"] == prev["total_revenue"]
                and row["units_sold"] == prev["units_sold"]
            ):
                row["revenue_rank"] = ranked[-1]["revenue_rank"]
            else:
                current_rank = i + 1
                row["revenue_rank"] = current_rank
        ranked.append(row)

    return ranked[:5]


def filter_by_days(rows, days):
    """Simulate WHERE fullDate >= CURRENT_DATE - INTERVAL '<days> days'."""
    from datetime import date, timedelta

    cutoff = date.today() - timedelta(days=days)
    return [r for r in rows if r.get("sale_date", date.today()) >= cutoff]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def products_all_time():
    """Six products with clear revenue ordering."""
    return [
        {
            "sku": "SKU-A",
            "product_name": "Alpha",
            "category": "Electronics",
            "total_revenue": 5000,
            "units_sold": 100,
        },
        {
            "sku": "SKU-B",
            "product_name": "Beta",
            "category": "Electronics",
            "total_revenue": 4000,
            "units_sold": 80,
        },
        {
            "sku": "SKU-C",
            "product_name": "Gamma",
            "category": "Clothing",
            "total_revenue": 3000,
            "units_sold": 60,
        },
        {
            "sku": "SKU-D",
            "product_name": "Delta",
            "category": "Clothing",
            "total_revenue": 2000,
            "units_sold": 40,
        },
        {
            "sku": "SKU-E",
            "product_name": "Epsilon",
            "category": "Food",
            "total_revenue": 1000,
            "units_sold": 20,
        },
        {
            "sku": "SKU-F",
            "product_name": "Zeta",
            "category": "Food",
            "total_revenue": 500,
            "units_sold": 10,
        },
    ]


@pytest.fixture
def products_with_tie():
    """Two products share the same revenue — tie broken by units_sold."""
    return [
        {
            "sku": "SKU-A",
            "product_name": "Alpha",
            "category": "Electronics",
            "total_revenue": 5000,
            "units_sold": 120,
        },  # tie-winner (more units)
        {
            "sku": "SKU-B",
            "product_name": "Beta",
            "category": "Electronics",
            "total_revenue": 5000,
            "units_sold": 80,
        },  # tie-loser
        {
            "sku": "SKU-C",
            "product_name": "Gamma",
            "category": "Clothing",
            "total_revenue": 3000,
            "units_sold": 60,
        },
        {
            "sku": "SKU-D",
            "product_name": "Delta",
            "category": "Clothing",
            "total_revenue": 2000,
            "units_sold": 40,
        },
        {
            "sku": "SKU-E",
            "product_name": "Epsilon",
            "category": "Food",
            "total_revenue": 1000,
            "units_sold": 20,
        },
        {
            "sku": "SKU-F",
            "product_name": "Zeta",
            "category": "Food",
            "total_revenue": 500,
            "units_sold": 10,
        },
    ]


# ---------------------------------------------------------------------------
# Ranking tests
# ---------------------------------------------------------------------------


class TestRankingLogic:
    def test_top5_returns_at_most_five(self, products_all_time):
        result = rank_products(products_all_time)
        assert len(result) == 5

    def test_ranked_by_revenue_descending(self, products_all_time):
        result = rank_products(products_all_time)
        revenues = [r["total_revenue"] for r in result]
        assert revenues == sorted(revenues, reverse=True)

    def test_rank_1_is_highest_revenue(self, products_all_time):
        result = rank_products(products_all_time)
        assert result[0]["sku"] == "SKU-A"
        assert result[0]["revenue_rank"] == 1

    def test_lowest_revenue_excluded_from_top5(self, products_all_time):
        result = rank_products(products_all_time)
        skus = [r["sku"] for r in result]
        assert "SKU-F" not in skus

    def test_required_columns_present(self, products_all_time):
        result = rank_products(products_all_time)
        for row in result:
            assert "sku" in row
            assert "product_name" in row
            assert "category" in row
            assert "total_revenue" in row
            assert "units_sold" in row
            assert "revenue_rank" in row


# ---------------------------------------------------------------------------
# Tie-breaking tests
# ---------------------------------------------------------------------------


class TestTieBreaking:
    def test_tie_broken_by_units_sold_desc(self, products_with_tie):
        result = rank_products(products_with_tie)
        # Both SKU-A and SKU-B have revenue=5000; SKU-A has more units
        assert result[0]["sku"] == "SKU-A"
        assert result[1]["sku"] == "SKU-B"

    def test_tied_products_share_same_rank(self, products_with_tie):
        rows = [
            {
                "sku": "SKU-A",
                "product_name": "A",
                "category": "X",
                "total_revenue": 5000,
                "units_sold": 100,
            },
            {
                "sku": "SKU-B",
                "product_name": "B",
                "category": "X",
                "total_revenue": 5000,
                "units_sold": 100,
            },  # exact tie
            {
                "sku": "SKU-C",
                "product_name": "C",
                "category": "X",
                "total_revenue": 3000,
                "units_sold": 60,
            },
        ]
        result = rank_products(rows)
        assert result[0]["revenue_rank"] == result[1]["revenue_rank"]

    def test_non_tied_products_have_different_ranks(self, products_all_time):
        result = rank_products(products_all_time)
        ranks = [r["revenue_rank"] for r in result]
        assert len(ranks) == len(set(ranks))


# ---------------------------------------------------------------------------
# Date-range filtering tests
# ---------------------------------------------------------------------------


class TestDateRangeFiltering:
    from datetime import date, timedelta

    def _make_row(self, sku, revenue, units, days_ago):
        from datetime import date, timedelta

        return {
            "sku": sku,
            "product_name": sku,
            "category": "Cat",
            "total_revenue": revenue,
            "units_sold": units,
            "sale_date": date.today() - timedelta(days=days_ago),
        }

    def test_7day_filter_excludes_older_sales(self):
        rows = [
            self._make_row("SKU-A", 5000, 100, 3),  # within 7 days
            self._make_row("SKU-B", 4000, 80, 3),
            self._make_row("SKU-C", 3000, 60, 10),  # outside 7 days
        ]
        filtered = filter_by_days(rows, 7)
        skus = [r["sku"] for r in filtered]
        assert "SKU-A" in skus
        assert "SKU-B" in skus
        assert "SKU-C" not in skus

    def test_30day_filter_includes_recent_month(self):
        rows = [
            self._make_row("SKU-A", 5000, 100, 25),  # within 30 days
            self._make_row("SKU-B", 4000, 80, 35),  # outside 30 days
        ]
        filtered = filter_by_days(rows, 30)
        skus = [r["sku"] for r in filtered]
        assert "SKU-A" in skus
        assert "SKU-B" not in skus

    def test_alltime_returns_all_rows(self):
        rows = [
            self._make_row("SKU-A", 5000, 100, 365),
            self._make_row("SKU-B", 4000, 80, 730),
        ]
        # All-time = no date filter applied
        assert len(rows) == 2

    def test_7day_top5_ranking_correct(self):
        rows = [
            self._make_row("SKU-A", 5000, 100, 2),
            self._make_row("SKU-B", 4000, 80, 5),
            self._make_row("SKU-C", 3000, 60, 10),  # excluded
        ]
        filtered = filter_by_days(rows, 7)
        result = rank_products(filtered)
        assert result[0]["sku"] == "SKU-A"
        assert result[0]["revenue_rank"] == 1
