# products/cards.py
TAB2_CARDS = [
    {"name": "Total Units Sold", "display": "scalar",
     "sql": 'SELECT COALESCE(SUM(total_units_sold),0) AS "Units Sold" FROM v_product_revenue;',
     "col": 0, "row": 0, "size_x": 8, "size_y": 3},
    {"name": "Active Products", "display": "scalar",
     "sql": 'SELECT COUNT(DISTINCT product_name) AS "Products" FROM v_product_revenue;',
     "col": 8, "row": 0, "size_x": 8, "size_y": 3},
    {"name": "Product Categories", "display": "scalar",
     "sql": 'SELECT COUNT(DISTINCT "categoryName") AS "Categories" FROM v_product_revenue;',
     "col": 16, "row": 0, "size_x": 8, "size_y": 3},
    {"name": "Top 10 Products by Revenue", "display": "bar",
     "sql": ('SELECT product_name AS "Product",'
             ' COALESCE(total_revenue,0) AS "Revenue (RWF)",'
             ' COALESCE(total_units_sold,0) AS "Units Sold"'
             ' FROM v_product_revenue WHERE revenue_rank <= 10'
             ' ORDER BY total_revenue DESC;'),
     "col": 0, "row": 3, "size_x": 14, "size_y": 7},
    {"name": "Revenue by Category", "display": "pie",
     "sql": ('SELECT "categoryName" AS "Category",'
             ' COALESCE(total_revenue,0) AS "Revenue (RWF)"'
             ' FROM v_category_revenue ORDER BY total_revenue DESC;'),
     "col": 14, "row": 3, "size_x": 10, "size_y": 7},
    {"name": "Top 5 Products — All Time", "display": "table",
     "sql": ('SELECT revenue_rank AS "Rank", sku AS "SKU",'
             ' product_name AS "Product", category AS "Category",'
             ' COALESCE(total_revenue,0) AS "Revenue (RWF)",'
             ' COALESCE(units_sold,0) AS "Units Sold"'
             ' FROM v_top5_products_all ORDER BY revenue_rank;'),
     "col": 0, "row": 10, "size_x": 14, "size_y": 7},
    {"name": "Turnover Ratio by Category", "display": "bar",
     "sql": ('SELECT category AS "Category",'
             ' COALESCE(turnover_ratio,0) AS "Turnover Ratio",'
             ' CASE WHEN below_threshold THEN \'⚠ Below \' || threshold'
             '      ELSE \'OK\' END AS "Status"'
             ' FROM v_category_turnover ORDER BY turnover_ratio ASC;'),
     "col": 14, "row": 10, "size_x": 10, "size_y": 7},
]
