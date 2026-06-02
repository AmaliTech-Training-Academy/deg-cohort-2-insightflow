-- InsightFlow Star Schema (OLAP Warehouse)
-- Target database: insightflow_star_schema
-- Idempotent: safe to run multiple times

-- ─────────────────────────────────────────────────────────────────────────────
-- DIMENSION TABLES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS dim_date (
    date_key         SERIAL       PRIMARY KEY,
    full_date        DATE         NOT NULL UNIQUE,
    year             INTEGER      NOT NULL,
    quarter          SMALLINT     NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month            SMALLINT     NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name       VARCHAR(20)  NOT NULL,
    week_number      SMALLINT     NOT NULL,
    day_name         VARCHAR(20)  NOT NULL,
    is_weekend       BOOLEAN      NOT NULL DEFAULT FALSE,
    is_public_holiday BOOLEAN     NOT NULL DEFAULT FALSE
);

-- SCD Type 2: tracks product changes over time
CREATE TABLE IF NOT EXISTS dim_product (
    product_key      SERIAL       PRIMARY KEY,
    product_sku      VARCHAR(100) NOT NULL,
    product_name     VARCHAR(255) NOT NULL,
    category_name    VARCHAR(100),
    valid_from       DATE         NOT NULL,
    valid_to         DATE,
    is_current       BOOLEAN      NOT NULL DEFAULT TRUE
);

-- SCD Type 2: tracks customer attribute changes over time
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_key     SERIAL       PRIMARY KEY,
    customer_id      INTEGER      NOT NULL,
    full_name        VARCHAR(255),
    email            VARCHAR(255),
    valid_from       DATE         NOT NULL,
    valid_to         DATE,
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS dim_store (
    store_key        SERIAL       PRIMARY KEY,
    store_id         INTEGER      NOT NULL UNIQUE,
    store_name       VARCHAR(255) NOT NULL,
    province         VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS dim_geography (
    geography_key    SERIAL       PRIMARY KEY,
    province         VARCHAR(100) NOT NULL,
    country          VARCHAR(100) NOT NULL,
    UNIQUE (province, country)
);

CREATE TABLE IF NOT EXISTS dim_channel (
    channel_key      SERIAL       PRIMARY KEY,
    channel_name     VARCHAR(100) NOT NULL UNIQUE,
    channel_type     VARCHAR(50)  NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_payment_method (
    payment_method_key SERIAL     PRIMARY KEY,
    method_name        VARCHAR(100) NOT NULL UNIQUE,
    method_type        VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS dim_order_status (
    order_status_key SERIAL       PRIMARY KEY,
    status_name      VARCHAR(100) NOT NULL UNIQUE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- FACT TABLES
-- ─────────────────────────────────────────────────────────────────────────────

-- Unified sales fact: covers both POS and online orders
CREATE TABLE IF NOT EXISTS fact_sales (
    sales_key            BIGSERIAL    PRIMARY KEY,
    date_key             INTEGER      NOT NULL REFERENCES dim_date(date_key),
    product_key          INTEGER      NOT NULL REFERENCES dim_product(product_key),
    customer_key         INTEGER               REFERENCES dim_customer(customer_key),
    store_key            INTEGER               REFERENCES dim_store(store_key),
    geography_key        INTEGER      NOT NULL REFERENCES dim_geography(geography_key),
    channel_key          INTEGER      NOT NULL REFERENCES dim_channel(channel_key),
    payment_method_key   INTEGER               REFERENCES dim_payment_method(payment_method_key),
    order_status_key     INTEGER               REFERENCES dim_order_status(order_status_key),
    source_transaction_id VARCHAR(100),
    quantity             INTEGER      NOT NULL CHECK (quantity > 0),
    unit_price           NUMERIC(12, 2) NOT NULL,
    discount_applied     NUMERIC(12, 2) NOT NULL DEFAULT 0,
    gross_amount         NUMERIC(14, 2) NOT NULL,
    net_amount           NUMERIC(14, 2) NOT NULL
);

-- Customer feedback / survey responses linked to online orders
CREATE TABLE IF NOT EXISTS fact_feedback (
    feedback_key         BIGSERIAL    PRIMARY KEY,
    date_key             INTEGER      NOT NULL REFERENCES dim_date(date_key),
    customer_key         INTEGER      NOT NULL REFERENCES dim_customer(customer_key),
    product_key          INTEGER               REFERENCES dim_product(product_key),
    geography_key        INTEGER               REFERENCES dim_geography(geography_key),
    source_order_id      VARCHAR(100),
    satisfaction_score   SMALLINT              CHECK (satisfaction_score BETWEEN 1 AND 10),
    nps_score            SMALLINT              CHECK (nps_score BETWEEN 0 AND 10),
    product_rating       SMALLINT              CHECK (product_rating BETWEEN 1 AND 5),
    delivery_rating      SMALLINT              CHECK (delivery_rating BETWEEN 1 AND 5),
    has_free_text        BOOLEAN      NOT NULL DEFAULT FALSE
);

-- Daily inventory snapshot per product / location
CREATE TABLE IF NOT EXISTS fact_inventory_snapshot (
    snapshot_key         BIGSERIAL    PRIMARY KEY,
    date_key             INTEGER      NOT NULL REFERENCES dim_date(date_key),
    product_key          INTEGER      NOT NULL REFERENCES dim_product(product_key),
    location_label       VARCHAR(255),
    stock_quantity       INTEGER      NOT NULL,
    reorder_threshold    INTEGER      NOT NULL,
    days_since_restock   INTEGER,
    is_below_reorder     BOOLEAN      NOT NULL DEFAULT FALSE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- INDEXES for common analytical query patterns
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_fact_sales_date        ON fact_sales(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product     ON fact_sales(product_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer    ON fact_sales(customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_channel     ON fact_sales(channel_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_geography   ON fact_sales(geography_key);

CREATE INDEX IF NOT EXISTS idx_fact_feedback_date     ON fact_feedback(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_feedback_customer ON fact_feedback(customer_key);

CREATE INDEX IF NOT EXISTS idx_fact_inv_date          ON fact_inventory_snapshot(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_inv_product       ON fact_inventory_snapshot(product_key);

CREATE INDEX IF NOT EXISTS idx_dim_product_sku        ON dim_product(product_sku);
CREATE INDEX IF NOT EXISTS idx_dim_product_current    ON dim_product(product_sku) WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_dim_customer_id        ON dim_customer(customer_id);
CREATE INDEX IF NOT EXISTS idx_dim_customer_current   ON dim_customer(customer_id) WHERE is_current = TRUE;
