"""
Bigtable → BigQuery export bridge.

Reads every row from the Bigtable 'prices' table and bulk-loads them into
BigQuery (price_intelligence_raw.prices), creating the table if it does not
exist.  This is the production path that feeds dbt.

Usage
-----
Local (emulator):
    BIGTABLE_EMULATOR_HOST=localhost:8086 \\
    GCP_PROJECT_ID=my-project \\
    python bigtable/export_to_bigquery.py

Production:
    GCP_PROJECT_ID=my-project \\
    BIGTABLE_INSTANCE_ID=price-intelligence \\
    BIGQUERY_DATASET=price_intelligence_raw \\
    python bigtable/export_to_bigquery.py

Options
-------
--project   GCP project ID          (default: $GCP_PROJECT_ID)
--instance  Bigtable instance ID    (default: $BIGTABLE_INSTANCE_ID or price-intelligence)
--dataset   BigQuery dataset        (default: $BIGQUERY_DATASET  or price_intelligence_raw)
--table     BigQuery table name     (default: prices)
--batch     Row batch size          (default: 5000)
--limit     Max rows to export (0 = all)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Iterator

COLUMN_FAMILY = "price_cf"
META_FAMILY = "metadata_cf"

_BQ_SCHEMA = [
    {"name": "product_id",   "type": "STRING",    "mode": "NULLABLE"},
    {"name": "source",       "type": "STRING",    "mode": "NULLABLE"},
    {"name": "url",          "type": "STRING",    "mode": "NULLABLE"},
    {"name": "title",        "type": "STRING",    "mode": "NULLABLE"},
    {"name": "price",        "type": "FLOAT64",   "mode": "NULLABLE"},
    {"name": "currency",     "type": "STRING",    "mode": "NULLABLE"},
    {"name": "rating",       "type": "FLOAT64",   "mode": "NULLABLE"},
    {"name": "availability", "type": "STRING",    "mode": "NULLABLE"},
    {"name": "category",     "type": "STRING",    "mode": "NULLABLE"},
    {"name": "image_url",    "type": "STRING",    "mode": "NULLABLE"},
    {"name": "scraped_at",   "type": "TIMESTAMP", "mode": "NULLABLE"},
    {"name": "exported_at",  "type": "TIMESTAMP", "mode": "NULLABLE"},
]


# ---------------------------------------------------------------------------
# Bigtable reader
# ---------------------------------------------------------------------------

def _iter_rows(project_id: str, instance_id: str, limit: int) -> Iterator[dict]:
    """Yield one dict per Bigtable row from the 'prices' table."""
    from google.cloud import bigtable  # noqa: PLC0415
    from google.cloud.bigtable import row_filters  # noqa: PLC0415

    client = bigtable.Client(project=project_id, admin=False)
    instance = client.instance(instance_id)
    table = instance.table("prices")

    row_filter = row_filters.CellsColumnLimitFilter(1)  # latest cell only
    exported_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    count = 0
    for row in table.read_rows(filter_=row_filter):
        record: dict = {"exported_at": exported_at}

        for family, cols in row.cells.items():
            for qualifier, cells in cols.items():
                if not cells:
                    continue
                key = qualifier.decode("utf-8") if isinstance(qualifier, bytes) else qualifier
                val = cells[0].value
                if isinstance(val, bytes):
                    try:
                        val = val.decode("utf-8")
                    except UnicodeDecodeError:
                        val = val.hex()
                # coerce numeric fields
                if key == "price":
                    try:
                        val = float(val)
                    except (TypeError, ValueError):
                        val = None
                elif key == "rating":
                    try:
                        val = float(val) if val not in ("", None) else None
                    except (TypeError, ValueError):
                        val = None
                record[key] = val

        yield record
        count += 1
        if limit and count >= limit:
            break

    client.close()


# ---------------------------------------------------------------------------
# BigQuery loader
# ---------------------------------------------------------------------------

def _load_rows(
    rows: list[dict],
    project_id: str,
    dataset: str,
    table_name: str,
) -> None:
    from google.cloud import bigquery  # noqa: PLC0415

    bq = bigquery.Client(project=project_id)
    table_id = f"{project_id}.{dataset}.{table_name}"

    # Ensure dataset exists
    ds_ref = bigquery.Dataset(f"{project_id}.{dataset}")
    ds_ref.location = os.environ.get("BIGQUERY_LOCATION", "US")
    bq.create_dataset(ds_ref, exists_ok=True)

    schema = [bigquery.SchemaField(f["name"], f["type"], mode=f["mode"]) for f in _BQ_SCHEMA]
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        ignore_unknown_values=True,
    )

    # Convert to JSONL bytes in memory (batches are capped, so this is safe)
    jsonl = "\n".join(json.dumps(r, default=str) for r in rows).encode("utf-8")
    import io  # noqa: PLC0415
    job = bq.load_table_from_file(io.BytesIO(jsonl), table_id, job_config=job_config)
    job.result()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(
    project_id: str,
    instance_id: str,
    dataset: str,
    table_name: str,
    batch_size: int,
    limit: int,
) -> None:
    print(f"[export] Bigtable {project_id}/{instance_id}/prices → BQ {dataset}.{table_name}")

    batch: list[dict] = []
    total = 0

    for record in _iter_rows(project_id, instance_id, limit):
        batch.append(record)
        if len(batch) >= batch_size:
            _load_rows(batch, project_id, dataset, table_name)
            total += len(batch)
            print(f"[export] {total:,} rows loaded …")
            batch = []

    if batch:
        _load_rows(batch, project_id, dataset, table_name)
        total += len(batch)

    print(f"[export] Done — {total:,} rows exported to BigQuery.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Export Bigtable prices → BigQuery")
    ap.add_argument("--project",  default=os.getenv("GCP_PROJECT_ID", ""),
                    help="GCP project ID")
    ap.add_argument("--instance", default=os.getenv("BIGTABLE_INSTANCE_ID", "price-intelligence"),
                    help="Bigtable instance ID")
    ap.add_argument("--dataset",  default=os.getenv("BIGQUERY_DATASET", "price_intelligence_raw"),
                    help="BigQuery dataset ID")
    ap.add_argument("--table",    default="prices",
                    help="BigQuery table name")
    ap.add_argument("--batch",    type=int, default=5000,
                    help="Rows per BigQuery load batch")
    ap.add_argument("--limit",    type=int, default=0,
                    help="Max rows to export (0 = all)")
    args = ap.parse_args()

    if not args.project:
        print("ERROR: --project or GCP_PROJECT_ID env var is required.", file=sys.stderr)
        sys.exit(1)

    run(
        project_id=args.project,
        instance_id=args.instance,
        dataset=args.dataset,
        table_name=args.table,
        batch_size=args.batch,
        limit=args.limit,
    )
