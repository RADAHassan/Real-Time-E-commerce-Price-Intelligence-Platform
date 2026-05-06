"""
JSONL-backed data store for local development.
Reads the real scraped data from data/**/*.jsonl instead of mock stubs.
Caches the loaded DataFrame for TTL seconds to avoid re-reading on every request.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd

# Underscore format (in JSONL) → dot format (API / frontend)
_REVERSE_SOURCE: dict[str, str] = {
    "books_toscrape": "books.toscrape.com",
    "scrapeme_live":  "scrapeme.live",
    "jumia_ma":       "jumia.ma",
    "ultrapc_ma":     "ultrapc.ma",
    "micromagma_ma":  "micromagma.ma",
    "cdiscount":      "cdiscount.com",
}

_ROOT      = Path(__file__).parent.parent
_DATA_DIR  = _ROOT / "data"
_CACHE_TTL = 120  # seconds

_cache: dict[str, Any] = {"df": None, "ts": 0.0}


def _load() -> pd.DataFrame:
    now = time.monotonic()
    if _cache["df"] is not None and now - _cache["ts"] < _CACHE_TTL:
        return _cache["df"]

    frames: list[pd.DataFrame] = []
    for path in _DATA_DIR.rglob("*.jsonl"):
        try:
            frames.append(pd.read_json(path, lines=True))
        except Exception:
            pass

    if not frames:
        _cache.update({"df": pd.DataFrame(), "ts": now})
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)

    # Normalise source names
    df["source"] = df["source"].map(lambda s: _REVERSE_SOURCE.get(str(s), str(s)))

    # Ensure required columns exist
    if "url"        not in df.columns: df["url"]        = df.apply(_build_url, axis=1)
    if "image_url"  not in df.columns: df["image_url"]  = ""
    if "rating"     not in df.columns: df["rating"]     = None
    if "category"   not in df.columns: df["category"]   = ""
    if "availability" not in df.columns: df["availability"] = "In stock"

    # Normalise scraped_at
    df["scraped_at"] = pd.to_datetime(df["scraped_at"], errors="coerce", utc=True)
    df = df.dropna(subset=["scraped_at", "price", "product_id"])
    df["scraped_date"] = df["scraped_at"].dt.date
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df[df["price"] > 0]

    _cache.update({"df": df, "ts": now})
    return df


def _build_url(row: pd.Series) -> str:
    source = str(row.get("source", ""))
    pid    = str(row.get("product_id", ""))
    return f"https://{source}/product/{pid}"


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    records = []
    for _, row in df.iterrows():
        records.append({
            "product_id":   str(row["product_id"]),
            "source":       str(row["source"]),
            "title":        str(row.get("title", "")),
            "url":          str(row.get("url", "")),
            "price":        float(row["price"]),
            "currency":     str(row.get("currency", "GBP")),
            "rating":       float(row["rating"]) if pd.notna(row.get("rating")) else None,
            "availability": str(row.get("availability", "In stock")),
            "category":     str(row.get("category", "")) or None,
            "scraped_at":   row["scraped_at"],
            "scraped_date": row["scraped_date"],
        })
    return records


def get_current_prices() -> list[dict]:
    """Latest observation per product_id across all sources."""
    df = _load()
    if df.empty:
        return []
    latest = df.sort_values("scraped_at").groupby("product_id", sort=False).last().reset_index()
    return _df_to_records(latest)


def get_price_history(product_id: str, days: int = 30) -> list[dict]:
    df = _load()
    if df.empty:
        return []
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    sub = df[(df["product_id"] == product_id) & (df["scraped_at"] >= cutoff)].sort_values("scraped_at")
    if sub.empty:
        # Return at least the single observation if it exists
        sub = df[df["product_id"] == product_id].sort_values("scraped_at")
    if sub.empty:
        return []

    sub = sub.copy()
    sub["prev_price"]       = sub["price"].shift(1)
    sub["price_change_abs"] = sub["price"] - sub["prev_price"]
    sub["price_change_pct"] = (sub["price_change_abs"] / sub["prev_price"] * 100).round(2)

    result = []
    for _, row in sub.iterrows():
        result.append({
            "product_id":       str(row["product_id"]),
            "price":            float(row["price"]),
            "prev_price":       float(row["prev_price"]) if pd.notna(row.get("prev_price")) else None,
            "price_change_pct": float(row["price_change_pct"]) if pd.notna(row.get("price_change_pct")) else None,
            "price_change_abs": float(row["price_change_abs"]) if pd.notna(row.get("price_change_abs")) else None,
            "scraped_date":     row["scraped_date"],
            "scraped_at":       row["scraped_at"],
        })
    return result


def get_stats() -> list[dict]:
    df = _load()
    if df.empty:
        return []

    result = []
    for source, grp in df.groupby("source"):
        prices = grp["price"]
        result.append({
            "source":           source,
            "currency":         str(grp["currency"].mode().iloc[0]) if not grp["currency"].empty else "GBP",
            "product_count":    int(grp["product_id"].nunique()),
            "observation_count": int(len(grp)),
            "avg_price":        round(float(prices.mean()), 2),
            "min_price":        round(float(prices.min()), 2),
            "max_price":        round(float(prices.max()), 2),
            "median_price":     round(float(prices.median()), 2),
            "p25_price":        round(float(prices.quantile(0.25)), 2),
            "p75_price":        round(float(prices.quantile(0.75)), 2),
            "stddev_price":     round(float(prices.std()), 2) if len(prices) > 1 else None,
            "first_seen_date":  grp["scraped_date"].min(),
            "last_updated_date": grp["scraped_date"].max(),
        })
    return sorted(result, key=lambda r: r["source"])


def get_alerts(min_drop_pct: float = 5.0) -> list[dict]:
    df = _load()
    if df.empty:
        return []

    df = df.sort_values(["product_id", "scraped_at"])
    df = df.copy()
    df["prev_price"] = df.groupby("product_id")["price"].shift(1)
    df = df.dropna(subset=["prev_price"])
    df["price_change_abs"] = df["price"] - df["prev_price"]
    df["price_change_pct"] = (df["price_change_abs"] / df["prev_price"] * 100).round(2)
    alerts = df[df["price_change_pct"] <= -min_drop_pct].sort_values("price_change_pct")

    result = []
    for _, row in alerts.iterrows():
        result.append({
            "product_id":       str(row["product_id"]),
            "source":           str(row["source"]),
            "title":            str(row.get("title", "")),
            "url":              str(row.get("url", "")),
            "currency":         str(row.get("currency", "GBP")),
            "current_price":    float(row["price"]),
            "prev_price":       float(row["prev_price"]),
            "price_change_pct": float(row["price_change_pct"]),
            "price_change_abs": float(row["price_change_abs"]),
            "alert_date":       row["scraped_date"],
            "scraped_at":       row["scraped_at"],
        })
    return result
