"""
ClickHouse client for the Price Intelligence Platform.

Usage:
    from clickhouse.client import ClickHouseClient
    client = ClickHouseClient()
    client.insert_items([{...}, {...}])
    df = client.query_df("SELECT * FROM prices LIMIT 100")
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_HOST     = os.environ.get("CLICKHOUSE_HOST", "localhost")
_PORT     = int(os.environ.get("CLICKHOUSE_PORT", "8123"))
_DATABASE = os.environ.get("CLICKHOUSE_DB", "price_intelligence")
_USER     = os.environ.get("CLICKHOUSE_USER", "default")
_PASSWORD = os.environ.get("CLICKHOUSE_PASSWORD", "price123")
_TABLE    = "prices"

_COLUMNS = [
    "product_id", "title", "price", "currency", "source",
    "url", "rating", "availability", "category", "image_url", "scraped_at",
]


class ClickHouseClient:
    def __init__(
        self,
        host: str = _HOST,
        port: int = _PORT,
        database: str = _DATABASE,
        username: str = _USER,
        password: str = _PASSWORD,
    ):
        import clickhouse_connect
        self._client = clickhouse_connect.get_client(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            connect_timeout=5,
        )
        self._database = database

    def insert_items(self, items: list[dict[str, Any]]) -> int:
        if not items:
            return 0
        rows = []
        for it in items:
            scraped_at = it.get("scraped_at")
            if scraped_at is None:
                scraped_at = datetime.now(timezone.utc)
            elif isinstance(scraped_at, str):
                try:
                    from datetime import datetime as dt
                    scraped_at = dt.fromisoformat(scraped_at.replace("Z", "+00:00"))
                except ValueError:
                    scraped_at = datetime.now(timezone.utc)

            rating = it.get("rating")
            rows.append([
                str(it.get("product_id") or ""),
                str(it.get("title") or ""),
                float(it.get("price") or 0.0),
                str(it.get("currency") or ""),
                str(it.get("source") or ""),
                str(it.get("url") or ""),
                float(rating) if rating is not None else None,
                str(it.get("availability") or ""),
                str(it.get("category") or ""),
                str(it.get("image_url") or ""),
                scraped_at,
            ])
        self._client.insert(_TABLE, rows, column_names=_COLUMNS)
        return len(rows)

    def query_df(self, sql: str):
        return self._client.query_df(sql)

    def row_count(self) -> int:
        result = self._client.command(f"SELECT count() FROM {_TABLE}")
        return int(result)

    def ping(self) -> bool:
        try:
            self._client.command("SELECT 1")
            return True
        except Exception:
            return False
