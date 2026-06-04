# regional/cards.py
TAB3_CARDS = [
    {"name": "Total Revenue (RWF)", "display": "scalar",
     "sql": ("SELECT COALESCE(ROUND(SUM(revenue),2),0) AS \"Total Revenue (RWF)\""
             " FROM v_regional_comparison;"),
     "col": 0, "row": 0, "size_x": 8, "size_y": 3},
    {"name": "Active Provinces", "display": "scalar",
     "sql": 'SELECT COUNT(DISTINCT region_name) AS "Provinces" FROM v_regional_comparison;',
     "col": 8, "row": 0, "size_x": 8, "size_y": 3},
    {"name": "Top Province", "display": "scalar",
     "sql": ('SELECT COALESCE(region_name,\'N/A\') AS "Top Province"'
             ' FROM v_regional_comparison ORDER BY revenue DESC LIMIT 1;'),
     "col": 16, "row": 0, "size_x": 8, "size_y": 3},
    {"name": "Revenue by Province", "display": "bar",
     "sql": ('SELECT region_name AS "Province",'
             ' COALESCE(revenue,0) AS "Revenue (RWF)",'
             ' COALESCE(transactions,0) AS "Transactions"'
             ' FROM v_regional_comparison ORDER BY revenue DESC;'),
     "col": 0, "row": 3, "size_x": 14, "size_y": 7},
    {"name": "Satisfaction & NPS by Province", "display": "bar",
     "sql": ('SELECT region_name AS "Province",'
             ' COALESCE(avg_satisfaction,0) AS "Satisfaction (1-5)",'
             ' COALESCE(nps_score,0) AS "NPS Score"'
             ' FROM v_regional_satisfaction ORDER BY avg_satisfaction DESC;'),
     "col": 14, "row": 3, "size_x": 10, "size_y": 7},
    {"name": "Regional Comparison", "display": "table",
     "sql": ('SELECT region AS "Region",'
             ' COALESCE(revenue,0) AS "Revenue (RWF)",'
             ' COALESCE(units_sold,0) AS "Units Sold",'
             ' COALESCE(transactions,0) AS "Transactions",'
             ' COALESCE(avg_satisfaction,0) AS "Satisfaction",'
             ' COALESCE(nps_score,0) AS "NPS"'
             ' FROM v_store_regional_comparison ORDER BY revenue DESC;'),
     "col": 0, "row": 10, "size_x": 24, "size_y": 7},
]
