{{ config(materialized='table') }}

-- Products whose price dropped by ≥ alert_drop_pct % in the last
-- alert_window_days days.  Ordered by largest drop first.
-- Powers the Alerts page in the Streamlit dashboard.
select
    product_id,
    source,
    title,
    url,
    currency,
    price                 as current_price,
    prev_price,
    price_change_pct,
    price_change_abs,
    prev_date,
    scraped_date          as alert_date,
    scraped_at
from {{ ref('int_price_changes') }}
where
    price_change_pct <= -{{ var('alert_drop_pct') }}
    and scraped_date >= date_sub(
            current_date(),
            interval {{ var('alert_window_days') }} day
        )
order by price_change_pct asc
