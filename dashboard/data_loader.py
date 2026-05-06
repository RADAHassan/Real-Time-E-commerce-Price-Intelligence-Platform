"""
Shared data-loading logic for the Streamlit dashboard.

Raw data priority:  ClickHouse → Bigtable emulator → local JSONL files
Mart data priority: ClickHouse views → BigQuery mart tables → JSONL aggregation

ClickHouse acts as the local data warehouse: the prices table is the raw layer,
the 4 mart_* views are the analytical layer (auto-updated at query time).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pandas as pd

# Map URL-style source names → canonical underscore names
_SOURCE_MAP = {
    "books.toscrape.com": "books_toscrape",
    "scrapeme.live":      "scrapeme_live",
    "jumia.ma":           "jumia_ma",
    "ultrapc.ma":         "ultrapc_ma",
    "micromagma.ma":      "micromagma_ma",
    "cdiscount.com":      "cdiscount",
}

def _norm_source(s: str) -> str:
    return _SOURCE_MAP.get(str(s).strip().lower(), str(s).strip())

def _norm_availability(s: str) -> str:
    """Collapse scrapy multi-line availability strings to a clean label."""
    s = re.sub(r"\s+", " ", str(s)).strip()
    sl = s.lower()
    if "out" in sl:
        return "Out of stock"
    if "pre" in sl:
        return "Pre-order"
    m = re.search(r"(\d+)", sl)
    if m:
        n = int(m.group(1))
        return f"{n} available" if n <= 5 else "In stock"
    return "In stock"

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))


# ──────────────────────────────────────────────────────────────────────────────
# Raw / live data  (ClickHouse → Bigtable → JSONL)
# ──────────────────────────────────────────────────────────────────────────────

def load_live(limit: int = 100_000) -> pd.DataFrame:
    """Return latest scraped rows. Priority: ClickHouse → Bigtable → JSONL."""
    df = _load_clickhouse(limit)
    if not df.empty:
        return df
    df = _load_bigtable(limit)
    if not df.empty:
        return df
    return _load_jsonl()


def _load_clickhouse(limit: int = 100_000) -> pd.DataFrame:
    try:
        from clickhouse.client import ClickHouseClient
        client = ClickHouseClient()
        if not client.ping():
            return pd.DataFrame()
        df = client.query_df(
            f"SELECT * FROM prices ORDER BY scraped_at DESC LIMIT {limit}"
        )
        if df.empty:
            return pd.DataFrame()
        return _clean(df)
    except Exception:
        return pd.DataFrame()


def _load_bigtable(limit: int = 5000) -> pd.DataFrame:
    try:
        from bigtable.client import BigtableClient
        client = BigtableClient(
            project_id=os.environ.get("GCP_PROJECT_ID", "local"),
            instance_id=os.environ.get("BIGTABLE_INSTANCE_ID", "price-intelligence"),
        )
        rows = list(client._table.read_rows(limit=limit))
        if not rows:
            return pd.DataFrame()
        records = [client._row_to_dict(r) for r in rows]
        df = pd.DataFrame(records)
        df["source"] = "bigtable"
        return _clean(df)
    except Exception:
        return pd.DataFrame()


def _load_jsonl() -> pd.DataFrame:
    data_dir = _ROOT / "data"
    frames: list[pd.DataFrame] = []
    for f in data_dir.rglob("*.jsonl"):
        try:
            frames.append(pd.read_json(f, lines=True))
        except Exception:
            pass
    if not frames:
        return pd.DataFrame()
    return _clean(pd.concat(frames, ignore_index=True))


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df["price"] = pd.to_numeric(df.get("price"), errors="coerce")
    df = df.dropna(subset=["price"])
    df = df[df["price"] >= 0]
    if "scraped_at" in df.columns:
        df["scraped_at"] = pd.to_datetime(df["scraped_at"], errors="coerce", utc=True)
        df["scraped_date"] = df["scraped_at"].dt.date
    if "source" not in df.columns and "spider" in df.columns:
        df["source"] = df["spider"]
    if "source" not in df.columns:
        df["source"] = "unknown"
    df["source"] = df["source"].apply(_norm_source)
    if "availability" in df.columns:
        df["availability"] = df["availability"].apply(_norm_availability)
    # Ensure product_id exists — fall back to title+source hash
    if "product_id" not in df.columns:
        df["product_id"] = (df.get("title", "").astype(str)
                            + "_" + df.get("source", "").astype(str)).str.lower().str.replace(r"\W+", "_", regex=True)
    if "title" not in df.columns:
        df["title"] = df["product_id"]
    if "currency" not in df.columns:
        df["currency"] = "GBP"
    return df.reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────────────
# Mart data (from BigQuery or JSONL aggregate)
# ──────────────────────────────────────────────────────────────────────────────

def load_mart(table: str) -> pd.DataFrame:
    """Load a mart table. Priority: ClickHouse view → BigQuery → JSONL aggregation."""
    df = _load_mart_clickhouse(table)
    if not df.empty:
        return df
    try:
        from google.cloud import bigquery
        project = os.environ["GCP_PROJECT_ID"]
        dataset = os.environ.get("BIGQUERY_DATASET", "price_intelligence") + "_marts"
        bq      = bigquery.Client(project=project)
        sql     = f"SELECT * FROM `{project}.{dataset}.{table}`"
        return bq.query(sql).to_dataframe()
    except Exception:
        return _build_mart_from_jsonl(table)


def _load_mart_clickhouse(table: str) -> pd.DataFrame:
    """Query a ClickHouse mart view by the same name used in BigQuery/dbt."""
    try:
        from clickhouse.client import ClickHouseClient
        client = ClickHouseClient()
        if not client.ping():
            return pd.DataFrame()
        return client.query_df(f"SELECT * FROM {table}")
    except Exception:
        return pd.DataFrame()


def _build_mart_from_jsonl(table: str) -> pd.DataFrame:
    df = _load_jsonl()
    if df.empty:
        return pd.DataFrame()

    if table == "mart_current_prices":
        idx = df.groupby("product_id")["scraped_at"].idxmax()
        return df.loc[idx].reset_index(drop=True)

    if table == "mart_price_stats":
        grp = df.groupby(["source", "currency"])["price"]
        return grp.agg(
            product_count="count",
            avg_price="mean",
            min_price="min",
            max_price="max",
            median_price="median",
            stddev_price="std",
        ).round(2).reset_index()

    if table == "mart_price_alerts":
        if "scraped_date" not in df.columns:
            return pd.DataFrame()
        df = df.sort_values(["product_id", "scraped_at"])
        df["prev_price"] = df.groupby("product_id")["price"].shift(1)
        df = df.dropna(subset=["prev_price"])
        df["price_change_pct"] = (df["price"] - df["prev_price"]) / df["prev_price"] * 100
        return df[df["price_change_pct"] <= -5].sort_values("price_change_pct")

    if table == "mart_price_history":
        df = df.sort_values(["product_id", "scraped_at"])
        df["prev_price"] = df.groupby("product_id")["price"].shift(1)
        df["price_change_pct"] = (
            (df["price"] - df["prev_price"]) / df["prev_price"] * 100
        ).round(2)
        return df

    return pd.DataFrame()
