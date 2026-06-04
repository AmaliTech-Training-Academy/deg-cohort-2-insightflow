# customer/cards.py
TAB4_CARDS = [
    {"name": "Total Customers", "display": "scalar",
     "sql": 'SELECT COUNT(DISTINCT "customerId") AS "Customers" FROM v_customer_performance;',
     "col": 0, "row": 0, "size_x": 8, "size_y": 3},
    {"name": "Total Customer Revenue (RWF)", "display": "scalar",
     "sql": ('SELECT COALESCE(ROUND(SUM(revenue),2),0)'
             ' AS "Total Revenue (RWF)" FROM v_customer_performance;'),
     "col": 8, "row": 0, "size_x": 8, "size_y": 3},
    {"name": "Avg Transactions per Customer", "display": "scalar",
     "sql": ('SELECT COALESCE(ROUND(AVG(transactions),1),0)'
             ' AS "Avg Transactions" FROM v_customer_performance;'),
     "col": 16, "row": 0, "size_x": 8, "size_y": 3},
    {"name": "Revenue by Segment", "display": "bar",
     "sql": ('SELECT segment AS "Segment",'
             ' COALESCE(revenue,0) AS "Revenue (RWF)",'
             ' COALESCE(total_customers,0) AS "Customers"'
             ' FROM v_customer_segments ORDER BY revenue DESC;'),
     "col": 0, "row": 3, "size_x": 14, "size_y": 7},
    {"name": "Customer Distribution by Segment", "display": "pie",
     "sql": ('SELECT segment AS "Segment",'
             ' COALESCE(total_customers,0) AS "Customers"'
             ' FROM v_customer_segments ORDER BY total_customers DESC;'),
     "col": 14, "row": 3, "size_x": 10, "size_y": 7},
    {"name": "Top 15 Customers by Revenue", "display": "table",
     "sql": ('SELECT "customerId" AS "Customer ID",'
             ' "fullName" AS "Name",'
             ' COALESCE(revenue,0) AS "Revenue (RWF)",'
             ' COALESCE(transactions,0) AS "Transactions",'
             ' COALESCE(avg_order_value,0) AS "Avg Order (RWF)"'
             ' FROM v_customer_performance ORDER BY revenue DESC LIMIT 15;'),
     "col": 0, "row": 10, "size_x": 24, "size_y": 7},
]
