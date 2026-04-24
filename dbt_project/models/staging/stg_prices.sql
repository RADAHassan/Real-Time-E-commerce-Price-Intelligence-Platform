{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw', 'prices') }}
),

cleaned as (
    select
        product_id,
        source,
        url,
        trim(title)                                     as title,
        cast(price as float64)                          as price,
        upper(trim(currency))                           as currency,
        cast(rating as float64)                         as rating,
        coalesce(nullif(trim(availability), ''), 'Unknown') as availability,
        nullif(trim(category), '')                      as category,
        nullif(image_url, '')                           as image_url,
        timestamp(scraped_at)                           as scraped_at,
        date(timestamp(scraped_at))                     as scraped_date
    from source
    where
        product_id   is not null
        and source   is not null
        and price    is not null
        and cast(price as float64) >= {{ var('min_price') }}
)

select * from cleaned
