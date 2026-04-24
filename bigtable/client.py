"""
BigtableClient — thin wrapper around google-cloud-bigtable for the price
intelligence platform.

Design choices:
  - Accepts an optional _table argument so tests can inject a mock directly.
  - All cell values are stored as UTF-8 strings (price as float repr).
  - Row decoding always converts 'price' and 'rating' back to float.
  - Timestamps on cells are explicit UTC datetimes — never let the library
    default to server-side timestamps, which breaks ordering guarantees.
"""

import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any

from google.cloud import bigtable

from bigtable.schema import TABLE_ID

logger = logging.getLogger(__name__)

# Column family → columns written by write_price_item()
_PRICE_COLS = ("price", "currency", "availability")
_META_COLS = ("title", "source", "url", "category", "image_url", "rating", "scraped_at")


def _make_row_key(product_id: str) -> bytes:
    """Build a row key with reversed-millisecond timestamp.

    Format: {product_id}#{reversed_ts_ms:019d}
    Reversed ts ensures the latest row sorts first in a prefix scan.
    """
    reversed_ms = sys.maxsize - int(time.time() * 1000)
    return f"{product_id}#{reversed_ms:019d}".encode()


def _cell_bytes(value: Any) -> bytes:
    if value is None:
        return b""
    return str(value).encode("utf-8")


class BigtableClient:
    """High-level client for reading and writing price observations."""

    TABLE_ID = TABLE_ID

    def __init__(self, project_id: str, instance_id: str, *, _table=None):
        if _table is not None:
            self._table = _table
        else:
            client = bigtable.Client(project=project_id, admin=False)
            self._table = client.instance(instance_id).table(self.TABLE_ID)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def write_price_item(self, item: dict) -> str:
        """Persist one PriceItem dict to Bigtable. Returns the row key string."""
        product_id = item.get("product_id", "")
        if not product_id:
            raise ValueError("item must contain a non-empty 'product_id'")

        row_key = _make_row_key(product_id)
        row = self._table.direct_row(row_key)
        ts = datetime.now(timezone.utc)

        # price_cf
        for col in _PRICE_COLS:
            row.set_cell("price_cf", col, _cell_bytes(item.get(col, "")), timestamp=ts)

        # metadata_cf
        for col in _META_COLS:
            row.set_cell("metadata_cf", col, _cell_bytes(item.get(col, "")), timestamp=ts)

        row.commit()
        logger.debug("Written row: %s", row_key.decode())
        return row_key.decode()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_latest_price(self, product_id: str) -> dict | None:
        """Return the most recent price record for a product, or None."""
        rows = list(self._scan_range(product_id, limit=1))
        return self._row_to_dict(rows[0]) if rows else None

    def scan_product_history(self, product_id: str, limit: int = 100) -> list[dict]:
        """Return all price observations for a product (latest first)."""
        return [self._row_to_dict(r) for r in self._scan_range(product_id, limit=limit)]

    def scan_all(self, limit: int = 1000) -> list[dict]:
        """Full table scan — for debugging only."""
        rows = self._table.read_rows(limit=limit)
        return [self._row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _scan_range(self, product_id: str, limit: int):
        """Read rows whose key starts with '{product_id}#'."""
        start = f"{product_id}#".encode()
        # End key: increment the last byte of the prefix to get an exclusive upper bound
        end = start[:-1] + bytes([start[-1] + 1])
        return self._table.read_rows(start_key=start, end_key=end, limit=limit)

    @staticmethod
    def _row_to_dict(row) -> dict:
        """Convert a Bigtable Row object to a plain Python dict."""
        result: dict[str, Any] = {"row_key": row.row_key.decode("utf-8")}

        for cf_id, columns in row.cells.items():
            for col_qualifier, cells in columns.items():
                if not cells:
                    continue
                col_name = (
                    col_qualifier.decode("utf-8")
                    if isinstance(col_qualifier, bytes)
                    else col_qualifier
                )
                value = cells[0].value.decode("utf-8", errors="replace")
                result[col_name] = value

        # Coerce numeric fields
        for num_field in ("price", "rating"):
            if num_field in result and result[num_field] not in ("", "None"):
                try:
                    result[num_field] = float(result[num_field])
                except ValueError:
                    pass

        return result
