-- InsightFlow Star Schema (OLAP Warehouse)
-- Target database: insightflow_star_schema
-- Idempotent: safe to run multiple times

-- ─────────────────────────────────────────────────────────────────────────────
-- DIMENSION TABLES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS "dimDate" (
    "dateKey"          SERIAL       PRIMARY KEY,
    "fullDate"         DATE         NOT NULL UNIQUE,
    "year"             INTEGER      NOT NULL,
    "quarter"          SMALLINT     NOT NULL CHECK ("quarter" BETWEEN 1 AND 4),
    "month"            SMALLINT     NOT NULL CHECK ("month" BETWEEN 1 AND 12),
    "monthName"        VARCHAR(20)  NOT NULL,
    "weekNumber"       SMALLINT     NOT NULL,
    "dayName"          VARCHAR(20)  NOT NULL,
    "isWeekend"        BOOLEAN      NOT NULL DEFAULT FALSE,
    "isPublicHoliday"  BOOLEAN      NOT NULL DEFAULT FALSE
);

-- SCD Type 2: tracks product changes over time
CREATE TABLE IF NOT EXISTS "dimProduct" (
    "productKey"       SERIAL       PRIMARY KEY,
    "productSKU"       VARCHAR(100) NOT NULL,
    "productName"      VARCHAR(255) NOT NULL,
    "categoryName"     VARCHAR(100),
    "validFrom"        DATE         NOT NULL,
    "validTo"          DATE,
    "isCurrent"        BOOLEAN      NOT NULL DEFAULT TRUE
);

-- SCD Type 2: tracks customer attribute changes over time
CREATE TABLE IF NOT EXISTS "dimCustomer" (
    "customerKey"      SERIAL       PRIMARY KEY,
    "customerId"       INTEGER      NOT NULL,
    "fullName"         VARCHAR(255),
    "email"            VARCHAR(255),
    "validFrom"        DATE         NOT NULL,
    "validTo"          DATE,
    "isActive"         BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS "dimStore" (
    "storeKey"         SERIAL       PRIMARY KEY,
    "storeId"          INTEGER      NOT NULL UNIQUE,
    "storeName"        VARCHAR(255) NOT NULL,
    "province"         VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS "dimGeography" (
    "geographyKey"     SERIAL       PRIMARY KEY,
    "province"         VARCHAR(100) NOT NULL,
    "country"          VARCHAR(100) NOT NULL,
    UNIQUE ("province", "country")
);

CREATE TABLE IF NOT EXISTS "dimChannel" (
    "channelKey"       SERIAL       PRIMARY KEY,
    "channelName"      VARCHAR(100) NOT NULL UNIQUE,
    "channelType"      VARCHAR(50)  NOT NULL
);

CREATE TABLE IF NOT EXISTS "dimPaymentMethod" (
    "paymentMethodKey" SERIAL       PRIMARY KEY,
    "methodName"       VARCHAR(100) NOT NULL UNIQUE,
    "methodType"       VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS "dimOrderStatus" (
    "orderStatusKey"   SERIAL       PRIMARY KEY,
    "statusName"       VARCHAR(100) NOT NULL UNIQUE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- FACT TABLES
-- ─────────────────────────────────────────────────────────────────────────────

-- Unified sales fact: covers both POS and online orders
CREATE TABLE IF NOT EXISTS "factSales" (
    "salesKey"             BIGSERIAL    PRIMARY KEY,
    "dateKey"              INTEGER      NOT NULL REFERENCES "dimDate"("dateKey"),
    "productKey"           INTEGER      NOT NULL REFERENCES "dimProduct"("productKey"),
    "customerKey"          INTEGER               REFERENCES "dimCustomer"("customerKey"),
    "storeKey"             INTEGER               REFERENCES "dimStore"("storeKey"),
    "geographyKey"         INTEGER      NOT NULL REFERENCES "dimGeography"("geographyKey"),
    "channelKey"           INTEGER      NOT NULL REFERENCES "dimChannel"("channelKey"),
    "paymentMethodKey"     INTEGER               REFERENCES "dimPaymentMethod"("paymentMethodKey"),
    "orderStatusKey"       INTEGER               REFERENCES "dimOrderStatus"("orderStatusKey"),
    "sourceTransactionId"  VARCHAR(100),
    "quantity"             INTEGER      NOT NULL CHECK ("quantity" > 0),
    "unitPrice"            NUMERIC(12, 2) NOT NULL,
    "discountApplied"      NUMERIC(12, 2) NOT NULL DEFAULT 0,
    "grossAmount"          NUMERIC(14, 2) NOT NULL,
    "netAmount"            NUMERIC(14, 2) NOT NULL
);

-- Customer feedback / survey responses linked to online orders
CREATE TABLE IF NOT EXISTS "factFeedback" (
    "feedbackKey"          BIGSERIAL    PRIMARY KEY,
    "dateKey"              INTEGER      NOT NULL REFERENCES "dimDate"("dateKey"),
    "customerKey"          INTEGER      NOT NULL REFERENCES "dimCustomer"("customerKey"),
    "productKey"           INTEGER               REFERENCES "dimProduct"("productKey"),
    "geographyKey"         INTEGER               REFERENCES "dimGeography"("geographyKey"),
    "sourceOrderId"        VARCHAR(100),
    "satisfactionScore"    SMALLINT              CHECK ("satisfactionScore" BETWEEN 1 AND 10),
    "npsScore"             SMALLINT              CHECK ("npsScore" BETWEEN 0 AND 10),
    "productRating"        SMALLINT              CHECK ("productRating" BETWEEN 1 AND 5),
    "deliveryRating"       SMALLINT              CHECK ("deliveryRating" BETWEEN 1 AND 5),
    "hasFreeText"          BOOLEAN      NOT NULL DEFAULT FALSE
);

-- Daily inventory snapshot per product / location
CREATE TABLE IF NOT EXISTS "factInventorySnapshot" (
    "snapshotKey"          BIGSERIAL    PRIMARY KEY,
    "dateKey"              INTEGER      NOT NULL REFERENCES "dimDate"("dateKey"),
    "productKey"           INTEGER      NOT NULL REFERENCES "dimProduct"("productKey"),
    "locationLabel"        VARCHAR(255),
    "stockQuantity"        INTEGER      NOT NULL,
    "reorderThreshold"     INTEGER      NOT NULL,
    "daysSinceRestock"     INTEGER,
    "isBelowReorder"       BOOLEAN      NOT NULL DEFAULT FALSE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- INDEXES for common analytical query patterns
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS "idxFactSalesDate"        ON "factSales"("dateKey");
CREATE INDEX IF NOT EXISTS "idxFactSalesProduct"     ON "factSales"("productKey");
CREATE INDEX IF NOT EXISTS "idxFactSalesCustomer"    ON "factSales"("customerKey");
CREATE INDEX IF NOT EXISTS "idxFactSalesChannel"     ON "factSales"("channelKey");
CREATE INDEX IF NOT EXISTS "idxFactSalesGeography"   ON "factSales"("geographyKey");

CREATE INDEX IF NOT EXISTS "idxFactFeedbackDate"     ON "factFeedback"("dateKey");
CREATE INDEX IF NOT EXISTS "idxFactFeedbackCustomer" ON "factFeedback"("customerKey");

CREATE INDEX IF NOT EXISTS "idxFactInvDate"          ON "factInventorySnapshot"("dateKey");
CREATE INDEX IF NOT EXISTS "idxFactInvProduct"       ON "factInventorySnapshot"("productKey");

CREATE INDEX IF NOT EXISTS "idxDimProductSKU"        ON "dimProduct"("productSKU");
CREATE INDEX IF NOT EXISTS "idxDimProductCurrent"    ON "dimProduct"("productSKU") WHERE "isCurrent" = TRUE;
CREATE INDEX IF NOT EXISTS "idxDimCustomerId"        ON "dimCustomer"("customerId");
CREATE INDEX IF NOT EXISTS "idxDimCustomerCurrent"   ON "dimCustomer"("customerId") WHERE "isCurrent" = TRUE;
