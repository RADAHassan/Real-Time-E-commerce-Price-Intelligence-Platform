{{ config(materialized='table') }}

-- Full price history with day-over-day change metrics.
-- Powers the time-series charts in the Streamlit dashboard.
select
    product_id,
    source,
    title,
    url,
    currency,
    price,
    prev_price,
    price_change_pct,
    price_change_abs,
    prev_date,
    scraped_date,
    scraped_at
from {{ ref('int_price_changes') }}
order by
    product_id,
    scraped_at
