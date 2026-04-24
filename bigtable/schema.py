"""
Bigtable schema initialisation for the price intelligence platform.

Table : prices
  Row key design : {product_id}#{reversed_ts_ms:019d}
    - product_id      : 32-char MD5 hex of the canonical product URL
    - '#'             : ASCII separator (chr 35) — stays between hex chars and digits
    - reversed_ts_ms  : sys.maxsize - epoch_ms, zero-padded to 19 digits
                        → latest observation comes FIRST in a prefix range scan

  Column families
    price_cf    — price (float str), currency (ISO 4217), availability
    metadata_cf — title, source, url, category, image_url, rating, scraped_at
    agg_cf      — reserved for Phase 5 (dbt/analytics computed KPIs)

The library auto-detects BIGTABLE_EMULATOR_HOST and routes to the local emulator.
"""

import logging

from google.cloud import bigtable
from google.cloud.bigtable.column_family import MaxVersionsGCRule

logger = logging.getLogger(__name__)

TABLE_ID = "prices"
COLUMN_FAMILIES = {
    "price_cf": MaxVersionsGCRule(1),
    "metadata_cf": MaxVersionsGCRule(1),
    "agg_cf": MaxVersionsGCRule(1),
}


def create_schema(project_id: str, instance_id: str, table_id: str = TABLE_ID) -> None:
    """Create the Bigtable table and column families.

    Idempotent — safe to re-run if the table already exists.
    """
    client = bigtable.Client(project=project_id, admin=True)
    instance = client.instance(instance_id)
    table = instance.table(table_id)

    if table.exists():
        logger.info("Table '%s' already exists — schema unchanged.", table_id)
        return

    table.create()
    logger.info("Table '%s' created.", table_id)

    for cf_name, gc_rule in COLUMN_FAMILIES.items():
        cf = table.column_family(cf_name, gc_rule=gc_rule)
        cf.create()
        logger.info("  Column family '%s' created.", cf_name)

    logger.info("Schema initialised: project=%s instance=%s table=%s", project_id, instance_id, table_id)


def drop_schema(project_id: str, instance_id: str, table_id: str = TABLE_ID) -> None:
    """Delete the table — for development resets only."""
    client = bigtable.Client(project=project_id, admin=True)
    instance = client.instance(instance_id)
    table = instance.table(table_id)

    if not table.exists():
        logger.warning("Table '%s' does not exist — nothing to drop.", table_id)
        return

    table.delete()
    logger.info("Table '%s' deleted.", table_id)
