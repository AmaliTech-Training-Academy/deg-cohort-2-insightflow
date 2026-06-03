# regional/cards.py
TAB3_CARDS = [
    {"name": "Total Revenue (RWF)", "display": "scalar",
     "sql": ("SELECT COALESCE(ROUND(SUM(revenue), 2), 0) AS \"Total Revenue (RWF)\" "
             "FROM v_country_comparison WHERE country = 'Rwanda';"),
     "col": 0, "row": 0, "size_x": 8, "size_y": 4},
    {"name": "Active Provinces", "display": "scalar",
     "sql": "SELECT COUNT(DISTINCT region_name) AS \"Provinces\" FROM v_regional_comparison;",
     "col": 8, "row": 0, "size_x": 8, "size_y": 4},
    {"name": "Top Province", "display": "scalar",
     "sql": "SELECT COALESCE(region_name, 'N/A') AS \"Top Province\" FROM v_regional_comparison ORDER BY revenue DESC LIMIT 1;",
     "col": 16, "row": 0, "size_x": 8, "size_y": 4},

    {"name": "Revenue by Province", "display": "bar",
     "sql": ("SELECT region_name AS \"Province\", "
             "COALESCE(revenue, 0) AS \"Revenue (RWF)\", "
             "COALESCE(transactions, 0) AS \"Transactions\" "
             "FROM v_regional_comparison ORDER BY revenue DESC;"),
     "col": 0, "row": 4, "size_x": 14, "size_y": 10},

    {"name": "Customer Reach by Province", "display": "bar",
     "sql": ("SELECT region_name AS \"Province\", "
             "COALESCE(unique_customers, 0) AS \"Unique Customers\", "
             "COALESCE(transactions, 0) AS \"Transactions\" "
             "FROM v_regional_comparison ORDER BY unique_customers DESC;"),
     "col": 14, "row": 4, "size_x": 10, "size_y": 10},

    {"name": "Avg Order Value by Province", "display": "bar",
     "sql": ("SELECT region_name AS \"Province\", "
             "COALESCE(avg_order_value, 0) AS \"Avg Order (RWF)\" "
             "FROM v_regional_comparison ORDER BY avg_order_value DESC;"),
     "col": 0, "row": 14, "size_x": 24, "size_y": 8},
]
