"""
chart_generator.py

Generates a server-side line chart of daily revenue (last 30 days) split
into two series: in-store and online.

Dependencies: matplotlib, psycopg2 (already in requirements)

Usage:
    python chart_generator.py                     # saves daily_revenue.png
    python chart_generator.py --out /tmp/rev.png  # custom output path
"""

from __future__ import annotations

import argparse
import io
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

# ---------------------------------------------------------------------------
# Data layer
# ---------------------------------------------------------------------------

SQL_DAILY_REVENUE_BY_CHANNEL = """
SELECT
    date,
    channel_type,
    COALESCE(SUM(daily_revenue), 0) AS revenue
FROM v_daily_revenue_by_channel
GROUP BY date, channel_type
ORDER BY date, channel_type;
"""


def fetch_series(conn) -> dict[str, Any]:
    """
    Query v_daily_revenue_by_channel and return a series dict.

    Returns:
        {
            "dates":    [date, ...],          # sorted, last 30 days
            "in_store": [float, ...],         # revenue per date
            "online":   [float, ...],         # revenue per date
        }
    """
    cutoff = date.today() - timedelta(days=30)
    all_dates = sorted(
        cutoff + timedelta(days=i) for i in range(31)
    )

    by_channel: dict[str, dict[date, float]] = defaultdict(
        lambda: defaultdict(float)
    )

    with conn.cursor() as cur:
        cur.execute(SQL_DAILY_REVENUE_BY_CHANNEL)
        for row_date, channel_type, revenue in cur.fetchall():
            if row_date >= cutoff:
                by_channel[channel_type][row_date] += float(revenue)

    return build_series(all_dates, by_channel)


def build_series(
    dates: list[date],
    by_channel: dict[str, dict[date, float]],
) -> dict[str, Any]:
    """
    Build the chart-ready series dict from raw channel buckets.

    Args:
        dates:      ordered list of date objects (the x-axis)
        by_channel: mapping of channel_type -> {date: revenue}

    Returns:
        {
            "dates":    [date, ...],
            "in_store": [float, ...],
            "online":   [float, ...],
        }

    Missing dates default to 0.0.
    Channel keys are matched case-insensitively; anything not matching
    "online" is treated as in-store.
    """
    in_store: dict[date, float] = defaultdict(float)
    online: dict[date, float] = defaultdict(float)

    for channel_type, daily in by_channel.items():
        target = online if "online" in channel_type.lower() else in_store
        for d, rev in daily.items():
            target[d] += rev

    return {
        "dates": dates,
        "in_store": [round(in_store[d], 2) for d in dates],
        "online": [round(online[d], 2) for d in dates],
    }


# ---------------------------------------------------------------------------
# Chart layer
# ---------------------------------------------------------------------------


def generate_chart(series: dict[str, Any], output_path: str | None = None) -> bytes:
    """
    Render a two-series line chart and return PNG bytes.

    Args:
        series:      output of build_series() / fetch_series()
        output_path: if given, also writes the PNG to this file path

    Returns:
        PNG image as bytes (suitable for HTTP response or file write).
    """
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend — no display required
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    dates = series["dates"]
    in_store = series["in_store"]
    online = series["online"]

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(dates, in_store, label="In-Store", color="#2563EB",
            linewidth=2, marker="o", markersize=4)
    ax.plot(dates, online, label="Online",   color="#16A34A",
            linewidth=2, marker="s", markersize=4)

    ax.set_title("Daily Revenue — Last 30 Days", fontsize=14, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Revenue (RWF)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    png_bytes = buf.read()

    if output_path:
        with open(output_path, "wb") as f:
            f.write(png_bytes)

    return png_bytes


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate daily revenue line chart as PNG"
    )
    parser.add_argument(
        "--out", default="daily_revenue.png", help="Output PNG file path"
    )
    args = parser.parse_args()

    import psycopg2
    from config import PG_CONFIG  # type: ignore[attr-defined]

    with psycopg2.connect(**PG_CONFIG) as conn:
        series = fetch_series(conn)

    png = generate_chart(series, output_path=args.out)
    print(f"Chart saved → {args.out} ({len(png):,} bytes)")


if __name__ == "__main__":
    main()
