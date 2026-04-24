-- Fail if any row has a scraped_at timestamp in the future.
-- Clock skew tolerance: allow up to 5 minutes ahead of current time.
select *
from {{ ref('stg_prices') }}
where scraped_at > timestamp_add(current_timestamp(), interval 5 minute)
