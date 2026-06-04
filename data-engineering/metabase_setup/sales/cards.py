# sales/cards.py
TAB1_CARDS = [
    {"name": "Total Revenue (RWF)", "display": "scalar",
     "sql": 'SELECT COALESCE(ROUND(total_revenue,2),0) AS "Total Revenue (RWF)" FROM v_kpi_summary;',
     "col": 0, "row": 0, "size_x": 6, "size_y": 3},
    {"name": "Total Transactions", "display": "scalar",
     "sql": 'SELECT COALESCE(total_transactions,0) AS "Transactions" FROM v_kpi_summary;',
     "col": 6, "row": 0, "size_x": 6, "size_y": 3},
    {"name": "Unique Customers", "display": "scalar",
     "sql": 'SELECT COALESCE(unique_customers,0) AS "Customers" FROM v_kpi_summary;',
     "col": 12, "row": 0, "size_x": 6, "size_y": 3},
    {"name": "Avg Order Value (RWF)", "display": "scalar",
     "sql": 'SELECT COALESCE(avg_order_value,0) AS "Avg Order (RWF)" FROM v_kpi_summary;',
     "col": 18, "row": 0, "size_x": 6, "size_y": 3},
    {"name": "Daily Revenue Trend", "display": "line",
     "sql": ('SELECT date,'
             ' COALESCE(daily_revenue,0) AS "Revenue (RWF)",'
             ' COALESCE(transactions,0) AS "Transactions"'
             ' FROM v_daily_revenue ORDER BY date;'),
     "col": 0, "row": 3, "size_x": 14, "size_y": 7},
    {"name": "In-Store vs Online (Last 30 Days)", "display": "bar",
     "sql": ('SELECT channel_type AS "Channel",'
             ' COALESCE(SUM(daily_revenue),0) AS "Revenue (RWF)",'
             ' COALESCE(SUM(transactions),0) AS "Transactions"'
             ' FROM v_daily_revenue_by_channel'
             ' GROUP BY channel_type ORDER BY 2 DESC;'),
     "col": 14, "row": 3, "size_x": 10, "size_y": 7},
    {"name": "Weekly Summary", "display": "table",
     "sql": ('SELECT week_start AS "Week Start",'
             ' COALESCE(weekly_revenue,0) AS "Revenue (RWF)",'
             ' COALESCE(transactions,0) AS "Transactions",'
             ' COALESCE(unique_customers,0) AS "Customers",'
             ' COALESCE(units_sold,0) AS "Units Sold",'
             ' COALESCE(avg_order_value,0) AS "Avg Order (RWF)"'
             ' FROM v_weekly_summary ORDER BY week_start DESC LIMIT 10;'),
     "col": 0, "row": 10, "size_x": 24, "size_y": 7},
]
