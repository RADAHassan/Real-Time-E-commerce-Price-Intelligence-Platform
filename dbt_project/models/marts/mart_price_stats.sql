{{ config(materialized='table') }}

-- Aggregate price statistics per (source, currency).
-- Refreshed daily by Airflow.  Feeds the KPI cards in the dashboard.
select
    source,
    currency,
    count(distinct product_id)                                as product_count,
    count(*)                                                  as observation_count,

    round(avg(price),    2)                                   as avg_price,
    round(min(price),    2)                                   as min_price,
    round(max(price),    2)                                   as max_price,
    round(stddev(price), 2)                                   as stddev_price,

    -- BigQuery APPROX_QUANTILES: returns (n+1)-element array
    round(approx_quantiles(price, 100)[offset(25)], 2)        as p25_price,
    round(approx_quantiles(price, 100)[offset(50)], 2)        as median_price,
    round(approx_quantiles(price, 100)[offset(75)], 2)        as p75_price,

    min(scraped_date)                                         as first_seen_date,
    max(scraped_date)                                         as last_updated_date
from {{ ref('int_prices_deduped') }}
group by 1, 2
