{{ config(materialized='ephemeral') }}

-- Keep only the most recent scrape per product per calendar day.
-- Multiple scrape runs on the same day produce duplicates that are
-- harmless for history but inflate counts in the mart models.
with ranked as (
    select
        *,
        row_number() over (
            partition by product_id, scraped_date
            order by scraped_at desc
        ) as rn
    from {{ ref('stg_prices') }}
)

select * except(rn)
from ranked
where rn = 1
