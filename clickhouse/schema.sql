-- ClickHouse schema for the Price Intelligence Platform
-- Auto-executed on container startup via /docker-entrypoint-initdb.d/

CREATE DATABASE IF NOT EXISTS price_intelligence;

-- =============================================================================
-- Raw layer — append-only scrape history
-- =============================================================================

CREATE TABLE IF NOT EXISTS price_intelligence.prices
(
    product_id   String,
    title        String,
    price        Float64,
    currency     LowCardinality(String),
    source       LowCardinality(String),
    url          String,
    rating       Nullable(Float64),
    availability LowCardinality(String),
    category     LowCardinality(String),
    image_url    String,
    scraped_at   DateTime64(3, 'UTC')
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(scraped_at)
ORDER BY (source, product_id, scraped_at)
SETTINGS index_granularity = 8192;

-- =============================================================================
-- Mart layer — analytical views (auto-reflect new data, no ETL job needed)
-- =============================================================================

-- Most recent price per product (argMax picks value at the latest timestamp)
CREATE VIEW IF NOT EXISTS price_intelligence.mart_current_prices AS
SELECT
    product_id,
    argMax(title,        scraped_at) AS title,
    argMax(price,        scraped_at) AS price,
    argMax(currency,     scraped_at) AS currency,
    argMax(source,       scraped_at) AS source,
    argMax(url,          scraped_at) AS url,
    argMax(rating,       scraped_at) AS rating,
    argMax(availability, scraped_at) AS availability,
    argMax(category,     scraped_at) AS category,
    max(scraped_at)                  AS scraped_at
FROM price_intelligence.prices
GROUP BY product_id;

-- Per-source aggregate statistics (mirrors dbt mart_price_stats)
CREATE VIEW IF NOT EXISTS price_intelligence.mart_price_stats AS
SELECT
    source,
    currency,
    count()                       AS product_count,
    round(avg(price),        2)   AS avg_price,
    min(price)                    AS min_price,
    max(price)                    AS max_price,
    round(median(price),     2)   AS median_price,
    round(stddevPop(price),  2)   AS stddev_price
FROM price_intelligence.prices
WHERE price > 0
GROUP BY source, currency;

-- Daily price per product — one row per (product, day) (mirrors dbt mart_price_history)
CREATE VIEW IF NOT EXISTS price_intelligence.mart_price_history AS
SELECT
    product_id,
    argMax(title,    scraped_at) AS title,
    argMax(source,   scraped_at) AS source,
    argMax(currency, scraped_at) AS currency,
    toDate(scraped_at)           AS scraped_date,
    round(avg(price), 4)         AS price
FROM price_intelligence.prices
WHERE price > 0
GROUP BY product_id, scraped_date
ORDER BY product_id, scraped_date;

-- Products with ≥5% price drop vs previous observation (mirrors dbt mart_price_alerts)
CREATE VIEW IF NOT EXISTS price_intelligence.mart_price_alerts AS
WITH daily AS (
    SELECT
        product_id,
        argMax(title,    scraped_at) AS title,
        argMax(source,   scraped_at) AS source,
        argMax(currency, scraped_at) AS currency,
        toDate(scraped_at)           AS scraped_date,
        round(avg(price), 4)         AS price
    FROM price_intelligence.prices
    WHERE price > 0
    GROUP BY product_id, scraped_date
),
with_lag AS (
    SELECT
        *,
        lagInFrame(price, 1, 0) OVER (
            PARTITION BY product_id ORDER BY scraped_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS prev_price
    FROM daily
)
SELECT
    product_id,
    title,
    source,
    currency,
    scraped_date,
    price,
    prev_price,
    round((price - prev_price) / prev_price * 100, 2) AS price_change_pct
FROM with_lag
WHERE prev_price > 0
  AND price_change_pct <= -5
ORDER BY price_change_pct ASC;
