-- ClickHouse schema for the Price Intelligence Platform
-- Auto-executed on container startup via /docker-entrypoint-initdb.d/

CREATE DATABASE IF NOT EXISTS price_intelligence;

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
