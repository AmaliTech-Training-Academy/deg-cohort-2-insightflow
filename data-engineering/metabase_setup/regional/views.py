# regional/views.py
"""
SQL Views for Regional Analysis tab
"""

VIEWS_SQL = """
-- Regional summary: transactions, units, revenue per province
CREATE OR REPLACE VIEW v_regional_comparison AS
SELECT
    g."province" AS region_name,
    g."country",
    COUNT(f."salesKey") AS transactions,
    SUM(f."quantity") AS units_sold,
    SUM(f."netAmount") AS revenue,
    ROUND(AVG(f."netAmount"), 2) AS avg_order_value,
    COUNT(DISTINCT f."customerKey") AS unique_customers
FROM "factSales" f
JOIN "dimGeography" g ON f."geographyKey" = g."geographyKey"
GROUP BY g."province", g."country"
ORDER BY revenue DESC;

-- Country-level summary
CREATE OR REPLACE VIEW v_country_comparison AS
SELECT
    g."country",
    COUNT(f."salesKey") AS transactions,
    SUM(f."quantity") AS units_sold,
    SUM(f."netAmount") AS revenue,
    ROUND(AVG(f."netAmount"), 2) AS avg_order_value,
    COUNT(DISTINCT f."customerKey") AS unique_customers
FROM "factSales" f
JOIN "dimGeography" g ON f."geographyKey" = g."geographyKey"
GROUP BY g."country"
ORDER BY revenue DESC;
"""
