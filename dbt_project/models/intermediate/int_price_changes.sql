{{ config(materialized='ephemeral') }}

-- Compute day-over-day price changes for every product using a LAG window.
-- Rows where prev_price is null are first observations (no change yet).
with history as (
    select
        product_id,
        source,
        title,
        url,
        price,
        currency,
        rating,
        availability,
        category,
        scraped_date,
        scraped_at,

        lag(price, 1) over (
            partition by product_id
            order by scraped_at
        ) as prev_price,

        lag(scraped_date, 1) over (
            partition by product_id
            order by scraped_at
        ) as prev_date

    from {{ ref('int_prices_deduped') }}
)

select
    *,
    {{ price_change_pct('price', 'prev_price') }} as price_change_pct,
    price - prev_price                            as price_change_abs
from history
