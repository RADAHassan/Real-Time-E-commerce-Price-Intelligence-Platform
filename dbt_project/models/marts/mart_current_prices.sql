{{ config(materialized='table') }}

-- Latest known price for every tracked product.
-- One row per product_id — the row with the most recent scraped_at timestamp.
with latest_ts as (
    select
        product_id,
        max(scraped_at) as latest_scraped_at
    from {{ ref('int_prices_deduped') }}
    group by product_id
)

select
    p.product_id,
    p.source,
    p.title,
    p.url,
    p.price,
    p.currency,
    p.rating,
    p.availability,
    p.category,
    p.scraped_at,
    p.scraped_date
from {{ ref('int_prices_deduped') }} p
inner join latest_ts l
    on  p.product_id   = l.product_id
    and p.scraped_at   = l.latest_scraped_at
