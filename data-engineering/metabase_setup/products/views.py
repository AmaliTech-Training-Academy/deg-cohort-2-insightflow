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

-- Top 5 products by revenue — all time (US-14 base)
-- Tie-breaking: revenue DESC, then units_sold DESC
CREATE OR REPLACE VIEW v_top5_products_all AS
SELECT
    p."productSKU"                                        AS sku,
    p."productName"                                       AS product_name,
    p."categoryName"                                      AS category,
    SUM(f."netAmount")                                    AS total_revenue,
    SUM(f."quantity")                                     AS units_sold,
    RANK() OVER (
        ORDER BY SUM(f."netAmount") DESC, SUM(f."quantity") DESC
    )                                                     AS revenue_rank
FROM "factSales" f
JOIN "dimProduct" p
    ON f."productKey" = p."productKey" AND p."isCurrent" = TRUE
GROUP BY p."productSKU", p."productName", p."categoryName"
ORDER BY total_revenue DESC, units_sold DESC
LIMIT 5;

-- Top 5 products — last 7 days
CREATE OR REPLACE VIEW v_top5_products_7d AS
SELECT
    p."productSKU"                                        AS sku,
    p."productName"                                       AS product_name,
    p."categoryName"                                      AS category,
    SUM(f."netAmount")                                    AS total_revenue,
    SUM(f."quantity")                                     AS units_sold,
    RANK() OVER (
        ORDER BY SUM(f."netAmount") DESC, SUM(f."quantity") DESC
    )                                                     AS revenue_rank
FROM "factSales" f
JOIN "dimProduct" p
    ON f."productKey" = p."productKey" AND p."isCurrent" = TRUE
JOIN "dimDate" d ON f."dateKey" = d."dateKey"
WHERE d."fullDate" >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY p."productSKU", p."productName", p."categoryName"
ORDER BY total_revenue DESC, units_sold DESC
LIMIT 5;

-- Top 5 products — last 30 days
CREATE OR REPLACE VIEW v_top5_products_30d AS
SELECT
    p."productSKU"                                        AS sku,
    p."productName"                                       AS product_name,
    p."categoryName"                                      AS category,
    SUM(f."netAmount")                                    AS total_revenue,
    SUM(f."quantity")                                     AS units_sold,
    RANK() OVER (
        ORDER BY SUM(f."netAmount") DESC, SUM(f."quantity") DESC
    )                                                     AS revenue_rank
FROM "factSales" f
JOIN "dimProduct" p
    ON f."productKey" = p."productKey" AND p."isCurrent" = TRUE
JOIN "dimDate" d ON f."dateKey" = d."dateKey"
WHERE d."fullDate" >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY p."productSKU", p."productName", p."categoryName"
ORDER BY total_revenue DESC, units_sold DESC
LIMIT 5;

-- Inventory turnover per category
--
-- Formula: turnover = units_sold / avg_inventory_level
--   units_sold      = SUM(factSales.quantity) for the period
--   avg_inventory   = AVG(factInventorySnapshot.stockQuantity) for the period
--
-- A configurable threshold (default 2.0) is stored in the view so cards
-- can filter or flag below-threshold categories.  Change the literal below
-- and re-run metabase_setup.py to propagate to all dashboards.
--
-- Recalculated: views are dropped and recreated on every ETL run via
-- metabase_setup.py create_views().
CREATE OR REPLACE VIEW v_category_turnover AS
WITH sales_by_category AS (
    SELECT
        p."categoryName"          AS category,
        SUM(f."quantity")         AS units_sold
    FROM "factSales" f
    JOIN "dimProduct" p ON f."productKey" = p."productKey"
    GROUP BY p."categoryName"
),
inventory_by_category AS (
    SELECT
        p."categoryName"              AS category,
        AVG(s."stockQuantity")        AS avg_inventory
    FROM "factInventorySnapshot" s
    JOIN "dimProduct" p ON s."productKey" = p."productKey"
    GROUP BY p."categoryName"
)
SELECT
    sc.category,
    sc.units_sold,
    ROUND(ic.avg_inventory, 2)                              AS avg_inventory,
    ROUND(
        sc.units_sold::numeric / NULLIF(ic.avg_inventory, 0), 2
    )                                                       AS turnover_ratio,
    2.0                                                     AS threshold,
    CASE
        WHEN sc.units_sold::numeric
             / NULLIF(ic.avg_inventory, 0) < 2.0
        THEN TRUE ELSE FALSE
    END                                                     AS below_threshold
FROM sales_by_category sc
JOIN inventory_by_category ic ON sc.category = ic.category
ORDER BY turnover_ratio ASC;

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
