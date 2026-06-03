# sales_dashboard_cards.py
# Chart colours
COLOUR_BLUE = "#1A56DB"
COLOUR_BLUE_LIGHT = "#3B82F6"

# Optional date-range filter injected into time-series queries via template tags
DATE_FILTER_SNIPPET = (
    "[[AND {col} >= SPLIT_PART({{{{date_range}}}},'~',1)::date]] "
    "[[AND {col} <= SPLIT_PART({{{{date_range}}}},'~',2)::date]]"
)
# GHS currency format
GHS_COLUMN_FORMAT = {
    "number_style": "currency",
    "currency": "GHS",
    "currency_style": "code",
    "decimals": 2,
}


def ghs_column_settings(*column_labels: str) -> dict:
    """Return column_settings dict applying GHS currency format to the given labels."""
    return {f'["name","{label}"]': GHS_COLUMN_FORMAT for label in column_labels}


# Template tag definition shared by all cards that support date filtering
DATE_TEMPLATE_TAG = {
    "date_range": {
        "id": "tt_dr",
        "name": "date_range",
        "display-name": "Date Range",
        "type": "text",
        "required": False,
    }
}


def date_parameter_mapping(card_id: int) -> list:
    """Wire the dashboard Date Range filter to a card's date_range template tag."""
    return [
        {
            "parameter_id": "p_date_range",
            "card_id": card_id,
            "target": ["variable", ["template-tag", "date_range"]],
        }
    ]


_daily_sql = (
    'SELECT date, daily_revenue AS "Revenue (GHS)" '  # nosec B608
    "FROM v_daily_revenue WHERE 1=1 "
    + DATE_FILTER_SNIPPET.format(col="date")
    + " ORDER BY date;"
)

_monthly_sql = (
    "SELECT TO_CHAR(month_start,'Mon YYYY') AS \"Month\","  # nosec B608
    'monthly_revenue AS "Revenue (GHS)" FROM v_monthly_revenue '
    "WHERE month_start < DATE_TRUNC('month', CURRENT_DATE) "
    + DATE_FILTER_SNIPPET.format(col="month_start")
    + " ORDER BY month_start;"
)

_weekly_sql = (
    'SELECT week_start AS "Week Start", week_end AS "Week End", '  # nosec B608
    'weekly_revenue AS "Revenue (GHS)", transactions AS "Transactions", '
    'unique_customers AS "Unique Customers", units_sold AS "Units Sold", '
    'avg_order_value AS "Avg Order (GHS)" FROM v_weekly_summary WHERE 1=1 '
    + DATE_FILTER_SNIPPET.format(col="week_start")
    + " ORDER BY week_start DESC LIMIT 12;"
)

CARDS: list[dict] = [
    # KPI scalars
    {
        "name": "Sales – Total Revenue",
        "display": "scalar",
        "sql": (
            'SELECT ROUND(total_revenue,2) AS "Total Revenue (GHS)"'
            " FROM v_kpi_summary;"
        ),
        "viz": {
            "card.title": "Total Revenue",
            "card.description": "All-time cumulative revenue",
            "scalar.decimals": 2,
            "column_settings": ghs_column_settings("Total Revenue (GHS)"),
        },
        "col": 0,
        "row": 0,
        "size_x": 5,
        "size_y": 5,
    },
    {
        "name": "Sales – Transactions",
        "display": "scalar",
        "sql": 'SELECT total_transactions AS "Transactions" FROM v_kpi_summary;',
        "viz": {
            "card.title": "Transactions",
            "card.description": "Completed sales orders",
        },
        "col": 5,
        "row": 0,
        "size_x": 5,
        "size_y": 5,
    },
    {
        "name": "Sales – Unique Customers",
        "display": "scalar",
        "sql": 'SELECT unique_customers AS "Customers" FROM v_kpi_summary;',
        "viz": {
            "card.title": "Unique Customers",
            "card.description": "Distinct buyers",
        },
        "col": 10,
        "row": 0,
        "size_x": 5,
        "size_y": 5,
    },
    {
        "name": "Sales – Units Sold",
        "display": "scalar",
        "sql": 'SELECT total_units_sold AS "Units Sold" FROM v_kpi_summary;',
        "viz": {
            "card.title": "Units Sold",
            "card.description": "Total product units dispatched",
        },
        "col": 15,
        "row": 0,
        "size_x": 4,
        "size_y": 5,
    },
    {
        "name": "Sales – Avg Order Value",
        "display": "scalar",
        "sql": 'SELECT avg_order_value AS "Avg Order (GHS)" FROM v_kpi_summary;',
        "viz": {
            "card.title": "Avg Order Value",
            "card.description": "Mean spend per transaction",
            "scalar.decimals": 2,
            "column_settings": ghs_column_settings("Avg Order (GHS)"),
        },
        "col": 19,
        "row": 0,
        "size_x": 5,
        "size_y": 5,
    },
    # Trend charts
    {
        "name": "Sales – Daily Revenue Trend",
        "display": "line",
        "sql": _daily_sql,
        "tags": DATE_TEMPLATE_TAG,
        "filters": date_parameter_mapping,
        "viz": {
            "graph.dimensions": ["date"],
            "graph.metrics": ["Revenue (GHS)"],
            "graph.x_axis.title_text": "Date",
            "graph.y_axis.title_text": "Revenue (GHS)",
            "graph.colors": [COLOUR_BLUE],
            "graph.label_value_frequency": "fit",
            "card.title": "Daily Revenue Trend",
            "card.description": "Revenue per day — zoom with the Date Range filter",
            "column_settings": ghs_column_settings("Revenue (GHS)"),
        },
        "col": 0,
        "row": 5,
        "size_x": 16,
        "size_y": 9,
    },
    {
        "name": "Sales – Monthly Revenue",
        "display": "bar",
        "sql": _monthly_sql,
        "tags": DATE_TEMPLATE_TAG,
        "filters": date_parameter_mapping,
        "viz": {
            "graph.dimensions": ["Month"],
            "graph.metrics": ["Revenue (GHS)"],
            "graph.x_axis.title_text": "Month",
            "graph.y_axis.title_text": "Revenue (GHS)",
            "graph.colors": [COLOUR_BLUE_LIGHT],
            "graph.label_value_frequency": "fit",
            "card.title": "Revenue by Month",
            "card.description": "Monthly totals — current month excluded",
            "column_settings": ghs_column_settings("Revenue (GHS)"),
        },
        "col": 16,
        "row": 5,
        "size_x": 8,
        "size_y": 9,
    },
    # Weekly summary table
    {
        "name": "Sales – Weekly Summary",
        "display": "table",
        "sql": _weekly_sql,
        "tags": DATE_TEMPLATE_TAG,
        "filters": date_parameter_mapping,
        "viz": {
            "card.title": "Weekly Performance",
            "card.description": "Last 12 weeks — revenue, orders, customers and units",
            "column_settings": ghs_column_settings("Revenue (GHS)", "Avg Order (GHS)"),
        },
        "col": 0,
        "row": 14,
        "size_x": 24,
        "size_y": 10,
    },
]
