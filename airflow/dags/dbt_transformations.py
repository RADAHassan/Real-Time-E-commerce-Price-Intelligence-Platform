"""
DAG: dbt_transformations
Purpose : (1) Load scraped JSONL files → BigQuery raw table.
          (2) Run dbt models in layer order (staging → intermediate → marts).
          (3) Test and generate docs.
          Waits for daily_full_scrape to finish.
Schedule: 03:00 UTC every day (1 h after scraping).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor

_DEFAULT_ARGS: dict = {
    "owner": "price_intelligence",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

_DBT_DIR = "/opt/airflow/dbt_project"
_DBT = f"cd {_DBT_DIR} && dbt"
_DATA_DIR = "/opt/airflow/data"
_RAW_DATASET = "price_intelligence_raw"
_RAW_TABLE = "prices"

_BQ_SCHEMA = [
    {"name": "product_id",   "type": "STRING"},
    {"name": "source",       "type": "STRING"},
    {"name": "url",          "type": "STRING"},
    {"name": "title",        "type": "STRING"},
    {"name": "price",        "type": "FLOAT64"},
    {"name": "currency",     "type": "STRING"},
    {"name": "rating",       "type": "FLOAT64"},
    {"name": "availability", "type": "STRING"},
    {"name": "category",     "type": "STRING"},
    {"name": "image_url",    "type": "STRING"},
    {"name": "scraped_at",   "type": "TIMESTAMP"},
]


def _load_jsonl_to_bigquery(**ctx) -> None:
    """Upload all scraped JSONL files to the BigQuery raw prices table."""
    import os
    from pathlib import Path

    from google.cloud import bigquery  # noqa: PLC0415

    project_id = os.environ["GCP_PROJECT_ID"]
    location   = os.environ.get("BIGQUERY_LOCATION", "US")

    bq = bigquery.Client(project=project_id)

    # Ensure raw dataset exists
    dataset_ref = bigquery.Dataset(f"{project_id}.{_RAW_DATASET}")
    dataset_ref.location = location
    bq.create_dataset(dataset_ref, exists_ok=True)

    table_id = f"{project_id}.{_RAW_DATASET}.{_RAW_TABLE}"
    schema   = [bigquery.SchemaField(f["name"], f["type"]) for f in _BQ_SCHEMA]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        time_partitioning=bigquery.TimePartitioning(field="scraped_at"),
        ignore_unknown_values=True,
    )

    jsonl_files = sorted(Path(_DATA_DIR).rglob("*.jsonl"))
    if not jsonl_files:
        print(f"No JSONL files found under {_DATA_DIR} — skipping BQ load")
        return

    loaded = 0
    for path in jsonl_files:
        with open(path, "rb") as fh:
            job = bq.load_table_from_file(fh, table_id, job_config=job_config)
            job.result()
        print(f"  Loaded {path.name} → {table_id}")
        loaded += 1

    print(f"BigQuery load complete: {loaded} file(s) → {table_id}")


with DAG(
    dag_id="dbt_transformations",
    default_args=_DEFAULT_ARGS,
    description="dbt staging → intermediate → marts + tests + docs generate",
    schedule_interval="0 3 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["dbt", "bigquery", "phase4"],
    max_active_runs=1,
    doc_md=__doc__,
) as dag:

    wait_for_scrape = ExternalTaskSensor(
        task_id="wait_for_daily_scrape",
        external_dag_id="daily_full_scrape",
        external_task_id="end",
        # look back up to 2 h in case scraping ran late
        execution_delta=timedelta(hours=1),
        timeout=7200,
        poke_interval=60,
        mode="reschedule",
        allowed_states=["success"],
        failed_states=["failed", "skipped"],
    )

    load_to_bq = PythonOperator(
        task_id="load_raw_to_bigquery",
        python_callable=_load_jsonl_to_bigquery,
    )

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"{_DBT} deps",
    )

    dbt_staging = BashOperator(
        task_id="dbt_run_staging",
        bash_command=f"{_DBT} run --select staging.*",
    )

    dbt_intermediate = BashOperator(
        task_id="dbt_run_intermediate",
        bash_command=f"{_DBT} run --select intermediate.*",
    )

    dbt_marts = BashOperator(
        task_id="dbt_run_marts",
        bash_command=f"{_DBT} run --select marts.*",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"{_DBT} test",
    )

    dbt_docs = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=f"{_DBT} docs generate",
    )

    (
        wait_for_scrape
        >> load_to_bq
        >> dbt_deps
        >> dbt_staging
        >> dbt_intermediate
        >> dbt_marts
        >> [dbt_test, dbt_docs]
    )
