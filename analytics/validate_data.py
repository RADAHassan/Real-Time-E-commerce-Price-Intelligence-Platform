"""
Great Expectations data quality suite for raw scraped price data.
Usage:
    python analytics/validate_data.py [--data-dir data/] [--fail-on-error]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

REQUIRED_COLUMNS = ["product_id", "price", "source", "title", "scraped_at"]
KNOWN_SOURCES = {
    "books_toscrape",
    "scrapeme_live",
    "jumia_ma",
    "ultrapc_ma",
    "micromagma_ma",
}


# ── Loader ────────────────────────────────────────────────────────────────────

def _load_jsonl(data_dir: Path) -> pd.DataFrame:
    frames = []
    for path in data_dir.rglob("*.jsonl"):
        try:
            frames.append(pd.read_json(path, lines=True))
        except Exception as exc:
            print(f"  [warn] Could not read {path}: {exc}")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def load_data(data_dir: Path) -> pd.DataFrame:
    try:
        from bigtable.client import BigtableClient
        import os

        client = BigtableClient(
            project_id=os.environ.get("GCP_PROJECT_ID", "local"),
            instance_id=os.environ.get("BIGTABLE_INSTANCE_ID", "price-intelligence"),
        )
        rows = list(client._table.read_rows(limit=50_000))
        if rows:
            df = pd.DataFrame([client._row_to_dict(r) for r in rows])
            print(f"  [bigtable] Loaded {len(df):,} rows")
            return df
    except Exception as exc:
        print(f"  [bigtable] Unavailable: {exc}")

    df = _load_jsonl(data_dir)
    if not df.empty:
        print(f"  [jsonl] Loaded {len(df):,} rows from {data_dir}")
    return df


# ── Expectations ──────────────────────────────────────────────────────────────

class Result:
    def __init__(self, name: str, passed: bool, detail: str = ""):
        self.name = name
        self.passed = passed
        self.detail = detail

    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        suffix = f"  ({self.detail})" if self.detail else ""
        return f"  [{status}] {self.name}{suffix}"


def run_suite(df: pd.DataFrame) -> list[Result]:
    results: list[Result] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        results.append(Result(name, passed, detail))

    # ── Schema ────────────────────────────────────────────────────────────────
    for col in REQUIRED_COLUMNS:
        check(
            f"column '{col}' exists",
            col in df.columns,
            f"missing" if col not in df.columns else "",
        )

    if df.empty:
        check("dataset is non-empty", False, "0 rows loaded")
        return results

    # ── Completeness ──────────────────────────────────────────────────────────
    for col in ["product_id", "price", "source"]:
        if col not in df.columns:
            continue
        null_pct = df[col].isna().mean() * 100
        check(
            f"'{col}' null rate < 1%",
            null_pct < 1.0,
            f"{null_pct:.1f}% nulls",
        )

    # ── Price range ───────────────────────────────────────────────────────────
    if "price" in df.columns:
        prices = pd.to_numeric(df["price"], errors="coerce").dropna()
        check("price column is numeric", not prices.empty, f"{prices.isna().sum()} non-numeric")
        check("all prices > 0", (prices > 0).all(), f"{(prices <= 0).sum()} zero/negative")
        check("price max < 1_000_000", prices.max() < 1_000_000, f"max={prices.max():.2f}")
        check("price min >= 0.01", prices.min() >= 0.01, f"min={prices.min():.4f}")

        # Outlier check: flag if > 5% of rows are extreme outliers (IQR fence)
        q1, q3 = prices.quantile(0.25), prices.quantile(0.75)
        iqr = q3 - q1
        outlier_rate = ((prices < q1 - 3 * iqr) | (prices > q3 + 3 * iqr)).mean() * 100
        check(
            "extreme price outliers < 5%",
            outlier_rate < 5.0,
            f"{outlier_rate:.1f}% extreme outliers",
        )

    # ── Source validity ───────────────────────────────────────────────────────
    if "source" in df.columns:
        unknown = set(df["source"].dropna().unique()) - KNOWN_SOURCES
        check(
            "all sources are known",
            len(unknown) == 0,
            f"unknown: {unknown}" if unknown else "",
        )
        src_counts = df["source"].value_counts()
        check(
            "each source has >= 5 records",
            (src_counts >= 5).all(),
            f"low-count sources: {src_counts[src_counts < 5].to_dict()}",
        )

    # ── product_id ────────────────────────────────────────────────────────────
    if "product_id" in df.columns:
        dup_rate = df["product_id"].duplicated().mean() * 100
        check(
            "product_id duplicate rate < 80%",
            dup_rate < 80.0,
            f"{dup_rate:.1f}% duplicates (expected for time-series)",
        )
        check(
            "product_id not all null",
            df["product_id"].notna().any(),
        )

    # ── Timestamps ────────────────────────────────────────────────────────────
    if "scraped_at" in df.columns:
        ts = pd.to_datetime(df["scraped_at"], errors="coerce", utc=True)
        null_ts = ts.isna().mean() * 100
        check("scraped_at null rate < 5%", null_ts < 5.0, f"{null_ts:.1f}% nulls")

        now_utc = datetime.now(timezone.utc)
        future_pct = (ts > now_utc).sum()
        check("no future scraped_at values", future_pct == 0, f"{future_pct} future rows")

        cutoff = pd.Timestamp("2020-01-01", tz="UTC")
        ancient_pct = (ts.dropna() < cutoff).mean() * 100
        check(
            "scraped_at >= 2020-01-01",
            ancient_pct == 0,
            f"{ancient_pct:.1f}% pre-2020",
        )

    # ── Title ─────────────────────────────────────────────────────────────────
    if "title" in df.columns:
        empty_titles = (df["title"].isna() | (df["title"].astype(str).str.strip() == "")).mean() * 100
        check("title empty rate < 5%", empty_titles < 5.0, f"{empty_titles:.1f}% empty")

    # ── Currency ─────────────────────────────────────────────────────────────
    if "currency" in df.columns:
        null_cur = df["currency"].isna().mean() * 100
        check("currency null rate < 10%", null_cur < 10.0, f"{null_cur:.1f}% nulls")

    # ── Rating ────────────────────────────────────────────────────────────────
    if "rating" in df.columns:
        ratings = pd.to_numeric(df["rating"], errors="coerce").dropna()
        if not ratings.empty:
            check(
                "rating in [0, 5]",
                ((ratings >= 0) & (ratings <= 5)).all(),
                f"out-of-range: {((ratings < 0) | (ratings > 5)).sum()}",
            )

    return results


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(results: list[Result], df: pd.DataFrame) -> int:
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    print()
    print("=" * 60)
    print("  GREAT EXPECTATIONS — Data Quality Report")
    print("=" * 60)
    print(f"  Dataset : {len(df):,} rows × {len(df.columns)} columns")
    print(f"  Checks  : {len(results)} total  |  {len(passed)} passed  |  {len(failed)} failed")
    print()

    if passed:
        print("  ── PASSED ──────────────────────────────────────────")
        for r in passed:
            print(r)

    if failed:
        print()
        print("  ── FAILED ──────────────────────────────────────────")
        for r in failed:
            print(r)

    print()
    print("=" * 60)
    score = round(len(passed) / len(results) * 100, 1) if results else 0
    print(f"  Quality score: {score}%  ({'OK' if not failed else 'NEEDS ATTENTION'})")
    print("=" * 60)
    return len(failed)


def save_json_report(results: list[Result], df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "rows": len(df),
        "columns": list(df.columns),
        "checks": [
            {"name": r.name, "passed": r.passed, "detail": r.detail}
            for r in results
        ],
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "score_pct": round(sum(1 for r in results if r.passed) / max(len(results), 1) * 100, 1),
    }
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"  JSON report → {out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Run GE-style data quality checks")
    parser.add_argument("--data-dir", default=str(ROOT / "data"), help="Path to JSONL data directory")
    parser.add_argument("--fail-on-error", action="store_true", help="Exit 1 if any check fails")
    parser.add_argument("--json-report", default=str(ROOT / "analytics" / "reports" / "ge_validation.json"))
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    print(f"Loading data from {data_dir} ...")
    df = load_data(data_dir)

    if df.empty:
        print("  [warn] No data found — running checks on empty DataFrame")

    results = run_suite(df)
    n_failed = print_report(results, df)
    save_json_report(results, df, Path(args.json_report))

    if args.fail_on_error and n_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
