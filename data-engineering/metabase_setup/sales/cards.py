# sales/cards.py
TAB1_CARDS = [
    {
        "name": "Total Revenue (RWF)",
        "display": "scalar",
        "sql": (
            "SELECT COALESCE(ROUND(total_revenue, 2), 0)"
            ' AS "Total Revenue (RWF)" FROM v_kpi_summary;'
        ),
        "col": 0,
        "row": 0,
        "size_x": 6,
        "size_y": 4,
    },
    {
        "name": "Total Transactions",
        "display": "scalar",
        "sql": (
            "SELECT COALESCE(total_transactions, 0)"
            ' AS "Transactions" FROM v_kpi_summary;'
        ),
        "col": 6,
        "row": 0,
        "size_x": 6,
        "size_y": 4,
    },
    {
        "name": "Unique Customers",
        "display": "scalar",
        "sql": (
            "SELECT COALESCE(unique_customers, 0)" ' AS "Customers" FROM v_kpi_summary;'
        ),
        "col": 12,
        "row": 0,
        "size_x": 6,
        "size_y": 4,
    },
    {
        "name": "Avg Order Value (RWF)",
        "display": "scalar",
        "sql": (
            "SELECT COALESCE(avg_order_value, 0)"
            ' AS "Avg Order (RWF)" FROM v_kpi_summary;'
        ),
        "col": 18,
        "row": 0,
        "size_x": 6,
        "size_y": 4,
    },
    {
        "name": "Daily Revenue Trend",
        "display": "line",
        "sql": (
            "SELECT date,"
            ' COALESCE(daily_revenue, 0) AS "Revenue (RWF)",'
            ' COALESCE(transactions, 0) AS "Transactions"'
            " FROM v_daily_revenue ORDER BY date;"
        ),
        "col": 0,
        "row": 4,
        "size_x": 14,
        "size_y": 8,
    },
    {
        "name": "Monthly Revenue",
        "display": "bar",
        "sql": (
            "SELECT TO_CHAR(month_start, 'Mon YYYY') AS \"Month\","
            ' COALESCE(monthly_revenue, 0) AS "Revenue (RWF)",'
            ' COALESCE(transactions, 0) AS "Transactions"'
            " FROM v_monthly_revenue"
            " WHERE month_start < DATE_TRUNC('month', CURRENT_DATE)"
            " ORDER BY month_start;"
        ),
        "col": 14,
        "row": 4,
        "size_x": 10,
        "size_y": 8,
    },
    {
        "name": "Weekly Summary",
        "display": "table",
        "sql": (
            'SELECT week_start AS "Week Start", week_end AS "Week End",'
            ' COALESCE(weekly_revenue, 0) AS "Revenue (RWF)",'
            ' COALESCE(transactions, 0) AS "Transactions",'
            ' COALESCE(unique_customers, 0) AS "Customers",'
            ' COALESCE(units_sold, 0) AS "Units Sold",'
            ' COALESCE(avg_order_value, 0) AS "Avg Order (RWF)"'
            " FROM v_weekly_summary ORDER BY week_start DESC LIMIT 12;"
        ),
        "col": 0,
        "row": 12,
        "size_x": 24,
        "size_y": 10,
    },
]
