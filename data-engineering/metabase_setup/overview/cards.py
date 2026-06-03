# overview/cards.py
TAB0_CARDS = [
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
        "name": "Revenue by Category",
        "display": "bar",
        "sql": (
            'SELECT "categoryName" AS "Category",'
            ' COALESCE(total_revenue, 0) AS "Revenue (RWF)"'
            " FROM v_category_revenue ORDER BY total_revenue DESC;"
        ),
        "col": 0,
        "row": 4,
        "size_x": 12,
        "size_y": 9,
    },
    {
        "name": "Revenue by Customer Segment",
        "display": "bar",
        "sql": (
            'SELECT segment AS "Segment",'
            ' COALESCE(revenue, 0) AS "Revenue (RWF)"'
            " FROM v_customer_segments ORDER BY revenue DESC;"
        ),
        "col": 12,
        "row": 4,
        "size_x": 12,
        "size_y": 9,
    },
    {
        "name": "Monthly Revenue Trend",
        "display": "line",
        "sql": (
            "SELECT TO_CHAR(month_start, 'Mon YYYY') AS \"Month\","
            ' COALESCE(monthly_revenue, 0) AS "Revenue (RWF)",'
            ' COALESCE(transactions, 0) AS "Transactions"'
            " FROM v_monthly_revenue"
            " WHERE month_start < DATE_TRUNC('month', CURRENT_DATE)"
            " ORDER BY month_start;"
        ),
        "col": 0,
        "row": 13,
        "size_x": 24,
        "size_y": 8,
    },
]
