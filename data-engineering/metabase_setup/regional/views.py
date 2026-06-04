# regional/views.py
"""
SQL Views for Regional Analysis tab
"""

VIEWS_SQL = """
-- Regional summary: transactions, units, revenue per province
CREATE OR REPLACE VIEW v_regional_comparison AS
SELECT
    g."province" AS region_name,
    COUNT(f."salesKey") AS transactions,
    SUM(f."quantity") AS units_sold,
    SUM(f."netAmount") AS revenue,
    ROUND(AVG(f."netAmount"), 2) AS avg_order_value,
    COUNT(DISTINCT f."customerKey") AS unique_customers
FROM "factSales" f
JOIN "dimGeography" g ON f."geographyKey" = g."geographyKey"
GROUP BY g."province"
ORDER BY revenue DESC;

-- Satisfaction scores per province (US-14)
-- Satisfaction = mean of productRating + deliveryRating (scale 1-5)
-- NPS = (promoters - detractors) / total * 100
--   promoters: npsScore >= 9, detractors: npsScore <= 6
CREATE OR REPLACE VIEW v_regional_satisfaction AS
SELECT
    g."province" AS region_name,
    COUNT(fb."feedbackKey") AS feedback_count,
    ROUND(
        (AVG(fb."productRating") + AVG(fb."deliveryRating")) / 2.0, 2
    ) AS avg_satisfaction,
    ROUND(AVG(fb."productRating"), 2) AS avg_product_rating,
    ROUND(AVG(fb."deliveryRating"), 2) AS avg_delivery_rating,
    ROUND(
        (
            COUNT(*) FILTER (WHERE fb."npsScore" >= 9)
            - COUNT(*) FILTER (WHERE fb."npsScore" <= 6)
        )::numeric / NULLIF(COUNT(*), 0) * 100,
        1
    ) AS nps_score,
    COUNT(*) FILTER (WHERE fb."npsScore" >= 9) AS promoters,
    COUNT(*) FILTER (WHERE fb."npsScore" <= 6) AS detractors,
    COUNT(*) FILTER (WHERE fb."npsScore" BETWEEN 7 AND 8) AS passives,
    CASE
        WHEN (AVG(fb."productRating") + AVG(fb."deliveryRating")) / 2.0 < 3.5
        THEN TRUE ELSE FALSE
    END AS below_threshold
FROM "factFeedback" fb
JOIN "dimGeography" g ON fb."geographyKey" = g."geographyKey"
GROUP BY g."province"
ORDER BY avg_satisfaction DESC;

-- Store-based regional comparison
-- Regions are drawn from dimGeography.province via factSales.geographyKey.
-- For online orders this is onlineOrder.shippingProvince; for POS it is
-- store.province. Using the same geography dimension for both sales and
-- satisfaction ensures the LEFT JOIN produces correct scores.
CREATE OR REPLACE VIEW v_store_regional_comparison AS
WITH store_sales AS (
    SELECT
        COALESCE(g."province", 'Unknown') AS region,
        SUM(f."netAmount")                AS revenue,
        SUM(f."quantity")                 AS units_sold,
        COUNT(f."salesKey")               AS transactions,
        COUNT(DISTINCT f."customerKey")   AS unique_customers
    FROM "factSales" f
    LEFT JOIN "dimGeography" g ON f."geographyKey" = g."geographyKey"
    GROUP BY g."province"
),
store_satisfaction AS (
    SELECT
        g."province"                                        AS region,
        ROUND(
            (AVG(fb."productRating") + AVG(fb."deliveryRating")) / 2.0, 2
        )                                                   AS avg_satisfaction,
        ROUND(
            (
                COUNT(*) FILTER (WHERE fb."npsScore" >= 9)
                - COUNT(*) FILTER (WHERE fb."npsScore" <= 6)
            )::numeric / NULLIF(COUNT(*), 0) * 100, 1
        )                                                   AS nps_score
    FROM "factFeedback" fb
    JOIN "dimGeography" g ON fb."geographyKey" = g."geographyKey"
    GROUP BY g."province"
)
SELECT
    ss.region,
    COALESCE(ss.revenue, 0)           AS revenue,
    COALESCE(ss.units_sold, 0)        AS units_sold,
    COALESCE(ss.transactions, 0)      AS transactions,
    COALESCE(ss.unique_customers, 0)  AS unique_customers,
    sf.avg_satisfaction,
    sf.nps_score
FROM store_sales ss
LEFT JOIN store_satisfaction sf ON ss.region = sf.region
ORDER BY ss.revenue DESC;

"""
