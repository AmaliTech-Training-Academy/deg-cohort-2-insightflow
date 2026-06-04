"""
Tests for the daily-revenue chart data-series output format.

Covers:
- Series structure and key presence
- Correct date range (last 30 days)
- In-store and online series length matches dates
- Missing dates default to 0.0
- Channel-type routing (case-insensitive)
- Revenue values are rounded floats
- PNG bytes output is a valid PNG file
"""

import io
from collections import defaultdict
from datetime import date, timedelta

import pytest

from metabase_setup.chart_generator import build_series, generate_chart


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _last_30_days():
    today = date.today()
    return sorted(today - timedelta(days=i) for i in range(30, -1, -1))


def _channel_map(entries):
    """Build {channel_type: {date: revenue}} from a list of (type, date, rev)."""
    result = defaultdict(lambda: defaultdict(float))
    for channel_type, d, rev in entries:
        result[channel_type][d] += rev
    return result


# ---------------------------------------------------------------------------
# Series structure tests
# ---------------------------------------------------------------------------


class TestSeriesStructure:
    def test_has_required_keys(self):
        dates = _last_30_days()
        series = build_series(dates, {})
        assert "dates" in series
        assert "in_store" in series
        assert "online" in series

    def test_dates_length_is_31(self):
        dates = _last_30_days()
        series = build_series(dates, {})
        assert len(series["dates"]) == 31

    def test_series_length_matches_dates(self):
        dates = _last_30_days()
        series = build_series(dates, {})
        assert len(series["in_store"]) == len(series["dates"])
        assert len(series["online"]) == len(series["dates"])

    def test_dates_are_sorted_ascending(self):
        dates = _last_30_days()
        series = build_series(dates, {})
        assert series["dates"] == sorted(series["dates"])

    def test_revenue_values_are_floats(self):
        dates = _last_30_days()
        channel = _channel_map([("In-Store", dates[0], 1000)])
        series = build_series(dates, channel)
        assert all(isinstance(v, float) for v in series["in_store"])
        assert all(isinstance(v, float) for v in series["online"])


# ---------------------------------------------------------------------------
# Date range tests
# ---------------------------------------------------------------------------


class TestDateRange:
    def test_today_is_last_date(self):
        dates = _last_30_days()
        series = build_series(dates, {})
        assert series["dates"][-1] == date.today()

    def test_first_date_is_30_days_ago(self):
        dates = _last_30_days()
        series = build_series(dates, {})
        assert series["dates"][0] == date.today() - timedelta(days=30)

    def test_no_gaps_in_date_sequence(self):
        dates = _last_30_days()
        series = build_series(dates, {})
        for i in range(1, len(series["dates"])):
            delta = series["dates"][i] - series["dates"][i - 1]
            assert delta.days == 1


# ---------------------------------------------------------------------------
# Missing date / zero-fill tests
# ---------------------------------------------------------------------------


class TestMissingDates:
    def test_missing_dates_default_to_zero(self):
        dates = _last_30_days()
        # Only one date has revenue — all others should be 0.0
        single_date = dates[5]
        channel = _channel_map([("In-Store", single_date, 500)])
        series = build_series(dates, channel)
        zeros = [v for i, v in enumerate(series["in_store"])
                 if series["dates"][i] != single_date]
        assert all(v == 0.0 for v in zeros)

    def test_present_date_has_correct_revenue(self):
        dates = _last_30_days()
        target = dates[10]
        channel = _channel_map([("In-Store", target, 1234.56)])
        series = build_series(dates, channel)
        idx = series["dates"].index(target)
        assert series["in_store"][idx] == 1234.56

    def test_empty_channels_all_zeros(self):
        dates = _last_30_days()
        series = build_series(dates, {})
        assert all(v == 0.0 for v in series["in_store"])
        assert all(v == 0.0 for v in series["online"])


# ---------------------------------------------------------------------------
# Channel routing tests
# ---------------------------------------------------------------------------


class TestChannelRouting:
    def test_online_type_routes_to_online_series(self):
        dates = _last_30_days()
        d = dates[0]
        channel = _channel_map([("online", d, 800)])
        series = build_series(dates, channel)
        assert series["online"][0] == 800.0
        assert series["in_store"][0] == 0.0

    def test_in_store_type_routes_to_in_store_series(self):
        dates = _last_30_days()
        d = dates[0]
        channel = _channel_map([("In-Store", d, 600)])
        series = build_series(dates, channel)
        assert series["in_store"][0] == 600.0
        assert series["online"][0] == 0.0

    def test_case_insensitive_online_match(self):
        dates = _last_30_days()
        d = dates[0]
        for label in ("ONLINE", "Online", "online", "E-Online"):
            channel = _channel_map([(label, d, 100)])
            series = build_series(dates, channel)
            assert series["online"][0] == 100.0, f"Failed for label: {label}"

    def test_unknown_channel_routes_to_in_store(self):
        dates = _last_30_days()
        d = dates[0]
        channel = _channel_map([("POS", d, 700)])
        series = build_series(dates, channel)
        assert series["in_store"][0] == 700.0
        assert series["online"][0] == 0.0

    def test_multiple_channels_aggregated_correctly(self):
        dates = _last_30_days()
        d = dates[0]
        channel = _channel_map([
            ("In-Store", d, 400),
            ("POS",      d, 200),   # also in-store
            ("online",   d, 300),
        ])
        series = build_series(dates, channel)
        assert series["in_store"][0] == 600.0
        assert series["online"][0] == 300.0

    def test_revenue_rounded_to_two_decimals(self):
        dates = _last_30_days()
        d = dates[0]
        channel = _channel_map([("online", d, 1 / 3)])
        series = build_series(dates, channel)
        assert series["online"][0] == round(1 / 3, 2)


# ---------------------------------------------------------------------------
# PNG export tests
# ---------------------------------------------------------------------------


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class TestPNGExport:
    def _make_series(self):
        dates = _last_30_days()
        d = dates[15]
        channel = _channel_map([
            ("In-Store", d, 5000),
            ("online",   d, 3000),
        ])
        return build_series(dates, channel)

    def test_returns_bytes(self):
        series = self._make_series()
        png = generate_chart(series)
        assert isinstance(png, bytes)

    def test_output_is_valid_png(self):
        series = self._make_series()
        png = generate_chart(series)
        assert png[:8] == PNG_MAGIC

    def test_png_is_non_empty(self):
        series = self._make_series()
        png = generate_chart(series)
        assert len(png) > 1000  # real PNG is always several KB

    def test_png_readable_by_pillow(self):
        pytest.importorskip("PIL", reason="Pillow not installed")
        from PIL import Image

        series = self._make_series()
        png = generate_chart(series)
        img = Image.open(io.BytesIO(png))
        assert img.format == "PNG"

    def test_saves_to_file(self, tmp_path):
        series = self._make_series()
        out = str(tmp_path / "chart.png")
        generate_chart(series, output_path=out)
        with open(out, "rb") as f:
            assert f.read()[:8] == PNG_MAGIC
