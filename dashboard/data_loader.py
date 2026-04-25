"""
Shared data-loading logic for the Streamlit dashboard.
Priority chain: Bigtable emulator → BigQuery mart tables → local JSONL files.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))


# ──────────────────────────────────────────────────────────────────────────────
# Raw / live data  (from Bigtable)
# ──────────────────────────────────────────────────────────────────────────────

def load_live(limit: int = 5000) -> pd.DataFrame:
    """Return latest scraped rows from Bigtable or JSONL fallback."""
    try:
        from bigtable.client import BigtableClient
        client = BigtableClient(
            project_id=os.environ.get("GCP_PROJECT_ID", "local"),
            instance_id=os.environ.get("BIGTABLE_INSTANCE_ID", "price-intelligence"),
        )
        rows = list(client._table.read_rows(limit=limit))
        if not rows:
            raise ValueError("Bigtable empty")
        records = [client._row_to_dict(r) for r in rows]
        df = pd.DataFrame(records)
        df["source"] = "bigtable"
        return _clean(df)
    except Exception:
        return _load_jsonl()


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
    """Load a dbt mart table from BigQuery or fall back to aggregating JSONL."""
    try:
        from google.cloud import bigquery
        project  = os.environ["GCP_PROJECT_ID"]
        dataset  = os.environ.get("BIGQUERY_DATASET", "price_intelligence") + "_marts"
        bq       = bigquery.Client(project=project)
        sql      = f"SELECT * FROM `{project}.{dataset}.{table}`"
        return bq.query(sql).to_dataframe()
    except Exception:
        return _build_mart_from_jsonl(table)


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
