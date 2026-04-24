-- A price change > 500 % or < -100 % almost certainly means a scraping error
-- (e.g., a price in the wrong currency or a malformed HTML value).
-- Rows where prev_price IS NULL are first observations and are excluded.
select *
from {{ ref('mart_price_history') }}
where
    prev_price is not null
    and (
        price_change_pct > 500
        or price_change_pct < -100
    )
