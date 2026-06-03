# products/cards.py
TAB2_CARDS = [
    {"name": "Total Units Sold",   "display": "scalar",
     "sql": "SELECT COALESCE(SUM(total_units_sold), 0) AS \"Units Sold\" FROM v_product_revenue;",
     "col": 0,  "row": 0, "size_x": 8, "size_y": 4},
    {"name": "Active Products",    "display": "scalar",
     "sql": "SELECT COUNT(DISTINCT product_name) AS \"Products\" FROM v_product_revenue;",
     "col": 8,  "row": 0, "size_x": 8, "size_y": 4},
    {"name": "Product Categories", "display": "scalar",
     "sql": "SELECT COUNT(DISTINCT \"categoryName\") AS \"Categories\" FROM v_product_revenue;",
     "col": 16, "row": 0, "size_x": 8, "size_y": 4},

    {"name": "Top 10 Products by Revenue", "display": "bar",
     "sql": ("SELECT product_name AS \"Product\", "
             "COALESCE(total_revenue, 0) AS \"Revenue (RWF)\", "
             "COALESCE(total_units_sold, 0) AS \"Units Sold\" "
             "FROM v_product_revenue WHERE revenue_rank <= 10 ORDER BY total_revenue DESC;"),
     "col": 0, "row": 4, "size_x": 14, "size_y": 10},

    {"name": "Revenue by Category", "display": "pie",
     "sql": ("SELECT \"categoryName\" AS \"Category\", "
             "COALESCE(total_revenue, 0) AS \"Revenue (RWF)\" "
             "FROM v_category_revenue ORDER BY total_revenue DESC;"),
     "col": 14, "row": 4, "size_x": 10, "size_y": 10},

    {"name": "Inventory Turnover", "display": "bar",
     "sql": ("SELECT product_name AS \"Product\", "
             "COALESCE(total_units_sold, 0) AS \"Units Sold\", "
             "COALESCE(avg_units_per_day, 0) AS \"Avg Units/Day\" "
             "FROM v_inventory_turnover ORDER BY total_units_sold DESC LIMIT 15;"),
     "col": 0, "row": 14, "size_x": 24, "size_y": 8},
]
