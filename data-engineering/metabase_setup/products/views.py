# products/views.py
"""
SQL Views for Products & Inventory tab
"""

VIEWS_SQL = """
-- Product revenue and sales summary
CREATE OR REPLACE VIEW v_product_revenue AS
SELECT
    p."productName" AS product_name,
    p."categoryName",
    SUM(f."netAmount") AS total_revenue,
    SUM(f."quantity") AS total_units_sold,
    COUNT(f."salesKey") AS total_transactions,
    ROUND(AVG(f."unitPrice"), 2) AS avg_unit_price,
    RANK() OVER (ORDER BY SUM(f."netAmount") DESC) AS revenue_rank
FROM "factSales" f
JOIN "dimProduct" p ON f."productKey" = p."productKey"
GROUP BY p."productName", p."categoryName"
ORDER BY total_revenue DESC;

-- Inventory turnover per product
CREATE OR REPLACE VIEW v_inventory_turnover AS
SELECT
    p."productName" AS product_name,
    p."categoryName",
    SUM(f."quantity") AS total_units_sold,
    COUNT(DISTINCT f."dateKey") AS active_sales_days,
    ROUND(
        SUM(f."quantity")::numeric / NULLIF(COUNT(DISTINCT f."dateKey"), 0), 2
    ) AS avg_units_per_day,
    SUM(f."netAmount") AS total_revenue
FROM "factSales" f
JOIN "dimProduct" p ON f."productKey" = p."productKey"
GROUP BY p."productName", p."categoryName"
ORDER BY total_units_sold DESC;

-- Revenue by product category
CREATE OR REPLACE VIEW v_category_revenue AS
SELECT
    p."categoryName",
    SUM(f."netAmount") AS total_revenue,
    SUM(f."quantity") AS total_units_sold
FROM "factSales" f
JOIN "dimProduct" p ON f."productKey" = p."productKey"
GROUP BY p."categoryName"
ORDER BY total_revenue DESC;
"""
