# sales/views.py
"""
SQL Views for Sales & Revenue tab
"""

VIEWS_SQL = """
-- KPI summary
CREATE OR REPLACE VIEW v_kpi_summary AS
SELECT
    SUM(f."netAmount")              AS total_revenue,
    COUNT(f."salesKey")             AS total_transactions,
    COUNT(DISTINCT f."customerKey") AS unique_customers,
    SUM(f."quantity")               AS total_units_sold,
    ROUND(AVG(f."netAmount"), 2)    AS avg_order_value
FROM "factSales" f
JOIN "dimDate" d ON f."dateKey" = d."dateKey";

-- Daily revenue
CREATE OR REPLACE VIEW v_daily_revenue AS
SELECT
    d."fullDate"       AS date,
    SUM(f."netAmount") AS daily_revenue,
    COUNT(f."salesKey") AS transactions
FROM "factSales" f
JOIN "dimDate" d ON f."dateKey" = d."dateKey"
GROUP BY d."fullDate"
ORDER BY d."fullDate";

-- Daily revenue by channel — last 30 days (completed sales only)
--
-- Metric definition:
--   daily_revenue = SUM(quantity × unit_price − discount_applied)
--                 = SUM(netAmount)  [netAmount is pre-computed identically]
--   Only rows with status = 'Completed' are included.
--   Channel split: in-store vs online (dimChannel.channelType).
--   Default window: last 30 days (extend via additional WHERE on date).
CREATE OR REPLACE VIEW v_daily_revenue_by_channel AS
SELECT
    d."fullDate"                                          AS date,
    ch."channelName"                                      AS channel,
    ch."channelType"                                      AS channel_type,
    COUNT(f."salesKey")                                   AS transactions,
    SUM(
        f."quantity" * f."unitPrice" - f."discountApplied"
    )                                                     AS daily_revenue,
    SUM(f."discountApplied")                              AS total_discount
FROM "factSales" f
JOIN "dimDate" d
    ON f."dateKey" = d."dateKey"
JOIN "dimChannel" ch
    ON f."channelKey" = ch."channelKey"
LEFT JOIN "dimOrderStatus" os
    ON f."orderStatusKey" = os."orderStatusKey"
WHERE (os."statusName" ILIKE 'completed' OR f."orderStatusKey" IS NULL)
  AND d."fullDate" >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY d."fullDate", ch."channelName", ch."channelType"
ORDER BY d."fullDate", ch."channelName";

-- Monthly revenue
CREATE OR REPLACE VIEW v_monthly_revenue AS
SELECT
    MAKE_DATE(d."year", d."month", 1) AS month_start,
    SUM(f."netAmount")                AS monthly_revenue,
    COUNT(f."salesKey")               AS transactions
FROM "factSales" f
JOIN "dimDate" d ON f."dateKey" = d."dateKey"
GROUP BY d."year", d."month"
ORDER BY d."year", d."month";

-- Weekly summary
CREATE OR REPLACE VIEW v_weekly_summary AS
SELECT
    MIN(d."fullDate")               AS week_start,
    MAX(d."fullDate")               AS week_end,
    SUM(f."netAmount")              AS weekly_revenue,
    COUNT(f."salesKey")             AS transactions,
    COUNT(DISTINCT f."customerKey") AS unique_customers,
    SUM(f."quantity")               AS units_sold,
    ROUND(AVG(f."netAmount"), 2)    AS avg_order_value
FROM "factSales" f
JOIN "dimDate" d ON f."dateKey" = d."dateKey"
GROUP BY d."year", d."weekNumber"
ORDER BY d."year", d."weekNumber";
"""
