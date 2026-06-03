# customer/views.py
"""
SQL Views for Customer Intelligence tab
"""

VIEWS_SQL = """
-- Customer segments summary (grouped by activity level)
CREATE OR REPLACE VIEW v_customer_segments AS
WITH per_customer AS (
    SELECT
        f."customerKey",
        COUNT(f."salesKey")        AS tx_count,
        SUM(f."netAmount")         AS revenue,
        AVG(f."netAmount")         AS avg_order_value,
        SUM(f."quantity")          AS units_sold
    FROM "factSales" f
    JOIN "dimCustomer" c ON f."customerKey" = c."customerKey"
    GROUP BY f."customerKey"
)
SELECT
    CASE
        WHEN tx_count >= 10 THEN 'High Value'
        WHEN tx_count >= 5  THEN 'Mid Value'
        ELSE 'Low Value'
    END AS segment,
    COUNT(DISTINCT "customerKey")  AS total_customers,
    SUM(tx_count)                  AS transactions,
    SUM(revenue)                   AS revenue,
    ROUND(AVG(avg_order_value), 2) AS avg_order_value,
    SUM(units_sold)                AS units_sold
FROM per_customer
GROUP BY segment
ORDER BY revenue DESC;

-- Customer performance (top individual customers)
CREATE OR REPLACE VIEW v_customer_performance AS
SELECT
    c."customerId",
    c."fullName",
    COUNT(f."salesKey") AS transactions,
    SUM(f."quantity") AS units_sold,
    SUM(f."netAmount") AS revenue,
    ROUND(AVG(f."netAmount"), 2) AS avg_order_value
FROM "factSales" f
JOIN "dimCustomer" c ON f."customerKey" = c."customerKey"
GROUP BY c."customerId", c."fullName"
ORDER BY revenue DESC;
"""
