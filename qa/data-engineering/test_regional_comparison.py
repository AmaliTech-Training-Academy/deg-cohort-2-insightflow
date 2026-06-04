"""
Tests for store-based regional comparison (dimStore.province as region).

Covers:
- Region aggregation: revenue, units sold, satisfaction, NPS per region
- CSV export format: headers, row values, delimiter, encoding
"""

import csv
import io

import pytest

# ---------------------------------------------------------------------------
# Pure-Python equivalents of the SQL view logic
# ---------------------------------------------------------------------------


def aggregate_regions(sales_rows, feedback_rows):
    """
    Aggregate sales and feedback per region (province from dimStore).

    Args:
        sales_rows: list of dicts with keys:
            province, net_amount, quantity, sale_key, customer_key
        feedback_rows: list of dicts with keys:
            province, product_rating, delivery_rating, nps_score

    Returns:
        List of region summary dicts sorted by revenue DESC.
    """
    from collections import defaultdict

    sales = defaultdict(
        lambda: {"revenue": 0, "units_sold": 0, "transactions": 0, "customers": set()}
    )
    for row in sales_rows:
        region = row.get("province") or "Unknown"
        sales[region]["revenue"] += row["net_amount"]
        sales[region]["units_sold"] += row["quantity"]
        sales[region]["transactions"] += 1
        sales[region]["customers"].add(row["customer_key"])

    feedback = defaultdict(lambda: {"ratings": [], "nps": []})
    for row in feedback_rows:
        region = row.get("province") or "Unknown"
        feedback[region]["ratings"].append(
            (row["product_rating"] + row["delivery_rating"]) / 2.0
        )
        feedback[region]["nps"].append(row["nps_score"])

    def nps_score(nps_list):
        if not nps_list:
            return None
        total = len(nps_list)
        promoters = sum(1 for s in nps_list if s >= 9)
        detractors = sum(1 for s in nps_list if s <= 6)
        return round((promoters - detractors) / total * 100, 1)

    regions = set(sales.keys()) | set(feedback.keys())
    result = []
    for region in regions:
        s = sales[region]
        f = feedback[region]
        avg_sat = (
            round(sum(f["ratings"]) / len(f["ratings"]), 2) if f["ratings"] else None
        )
        result.append(
            {
                "region": region,
                "revenue": round(s["revenue"], 2),
                "units_sold": s["units_sold"],
                "transactions": s["transactions"],
                "unique_customers": len(s["customers"]),
                "avg_satisfaction": avg_sat,
                "nps_score": nps_score(f["nps"]),
            }
        )
    return sorted(result, key=lambda r: r["revenue"], reverse=True)


CSV_HEADERS = [
    "Region",
    "Revenue (RWF)",
    "Units Sold",
    "Transactions",
    "Unique Customers",
    "Avg Satisfaction (1-5)",
    "NPS Score",
]


def export_to_csv(rows):
    """
    Convert region summary rows to a CSV string.

    Returns:
        str: UTF-8 CSV with headers matching the Metabase table card columns.
    """
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=CSV_HEADERS,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "Region": row["region"],
                "Revenue (RWF)": row["revenue"],
                "Units Sold": row["units_sold"],
                "Transactions": row["transactions"],
                "Unique Customers": row["unique_customers"],
                "Avg Satisfaction (1-5)": row.get("avg_satisfaction", ""),
                "NPS Score": row.get("nps_score", ""),
            }
        )
    return output.getvalue()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _sale(province, net_amount, quantity, customer_key):
    return {
        "province": province,
        "net_amount": net_amount,
        "quantity": quantity,
        "sale_key": id(object()),
        "customer_key": customer_key,
    }


def _feedback(province, product_rating, delivery_rating, nps_score):
    return {
        "province": province,
        "product_rating": product_rating,
        "delivery_rating": delivery_rating,
        "nps_score": nps_score,
    }


@pytest.fixture
def sales_data():
    return [
        _sale("Kigali", 5000, 50, "C1"),
        _sale("Kigali", 3000, 30, "C2"),
        _sale("Eastern", 2000, 20, "C3"),
        _sale("Northern", 1000, 10, "C1"),
    ]


@pytest.fixture
def feedback_data():
    return [
        _feedback("Kigali", 5, 4, 10),
        _feedback("Kigali", 4, 5, 9),
        _feedback("Eastern", 3, 2, 5),
        _feedback("Northern", 4, 4, 7),
    ]


@pytest.fixture
def aggregated(sales_data, feedback_data):
    return aggregate_regions(sales_data, feedback_data)


# ---------------------------------------------------------------------------
# Region aggregation tests
# ---------------------------------------------------------------------------


class TestRegionAggregation:
    def test_sorted_by_revenue_descending(self, aggregated):
        revenues = [r["revenue"] for r in aggregated]
        assert revenues == sorted(revenues, reverse=True)

    def test_revenue_summed_correctly(self, aggregated):
        kigali = next(r for r in aggregated if r["region"] == "Kigali")
        assert kigali["revenue"] == 8000

    def test_units_sold_summed_correctly(self, aggregated):
        kigali = next(r for r in aggregated if r["region"] == "Kigali")
        assert kigali["units_sold"] == 80

    def test_transactions_counted_correctly(self, aggregated):
        eastern = next(r for r in aggregated if r["region"] == "Eastern")
        assert eastern["transactions"] == 1

    def test_unique_customers_deduplicated(self, aggregated):
        # C1 appears in both Kigali and Northern but each region counted once
        kigali = next(r for r in aggregated if r["region"] == "Kigali")
        assert kigali["unique_customers"] == 2

    def test_avg_satisfaction_computed(self, aggregated):
        kigali = next(r for r in aggregated if r["region"] == "Kigali")
        # ratings: (5+4)/2=4.5 and (4+5)/2=4.5 → avg=4.5
        assert kigali["avg_satisfaction"] == 4.5

    def test_nps_score_computed(self, aggregated):
        kigali = next(r for r in aggregated if r["region"] == "Kigali")
        # 2 promoters, 0 detractors → NPS = 100
        assert kigali["nps_score"] == 100.0

    def test_region_with_no_feedback_has_none_satisfaction(self):
        sales = [_sale("Western", 500, 5, "C9")]
        result = aggregate_regions(sales, [])
        western = result[0]
        assert western["avg_satisfaction"] is None
        assert western["nps_score"] is None

    def test_unknown_province_grouped_together(self):
        sales = [
            _sale(None, 1000, 10, "C1"),
            _sale(None, 500, 5, "C2"),
        ]
        result = aggregate_regions(sales, [])
        assert len(result) == 1
        assert result[0]["region"] == "Unknown"
        assert result[0]["revenue"] == 1500

    def test_required_columns_present(self, aggregated):
        for row in aggregated:
            for col in (
                "region",
                "revenue",
                "units_sold",
                "transactions",
                "unique_customers",
                "avg_satisfaction",
                "nps_score",
            ):
                assert col in row


# ---------------------------------------------------------------------------
# CSV export tests
# ---------------------------------------------------------------------------


class TestCSVExport:
    def _parse(self, csv_string):
        reader = csv.DictReader(io.StringIO(csv_string))
        return list(reader)

    def test_csv_has_correct_headers(self, aggregated):
        csv_str = export_to_csv(aggregated)
        first_line = csv_str.splitlines()[0]
        for header in CSV_HEADERS:
            assert header in first_line

    def test_csv_row_count_matches_regions(self, aggregated):
        csv_str = export_to_csv(aggregated)
        rows = self._parse(csv_str)
        assert len(rows) == len(aggregated)

    def test_csv_revenue_value_correct(self, aggregated):
        csv_str = export_to_csv(aggregated)
        rows = self._parse(csv_str)
        kigali = next(r for r in rows if r["Region"] == "Kigali")
        assert float(kigali["Revenue (RWF)"]) == 8000

    def test_csv_units_sold_correct(self, aggregated):
        csv_str = export_to_csv(aggregated)
        rows = self._parse(csv_str)
        kigali = next(r for r in rows if r["Region"] == "Kigali")
        assert int(kigali["Units Sold"]) == 80

    def test_csv_uses_comma_delimiter(self, aggregated):
        csv_str = export_to_csv(aggregated)
        first_line = csv_str.splitlines()[0]
        assert "," in first_line

    def test_csv_sorted_by_revenue_descending(self, aggregated):
        csv_str = export_to_csv(aggregated)
        rows = self._parse(csv_str)
        revenues = [float(r["Revenue (RWF)"]) for r in rows]
        assert revenues == sorted(revenues, reverse=True)

    def test_csv_empty_satisfaction_when_no_feedback(self):
        sales = [_sale("Western", 500, 5, "C9")]
        rows = aggregate_regions(sales, [])
        csv_str = export_to_csv(rows)
        parsed = self._parse(csv_str)
        assert parsed[0]["Avg Satisfaction (1-5)"] == ""
        assert parsed[0]["NPS Score"] == ""

    def test_csv_is_valid_utf8(self, aggregated):
        csv_str = export_to_csv(aggregated)
        assert isinstance(csv_str.encode("utf-8"), bytes)

    def test_csv_header_order_matches_spec(self, aggregated):
        csv_str = export_to_csv(aggregated)
        actual_headers = csv_str.splitlines()[0].split(",")
        assert actual_headers == CSV_HEADERS
