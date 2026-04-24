"""
DAG: dbt_transformations
Purpose : Run dbt models in layer order (staging → intermediate → marts),
          then test and generate docs.  Waits for daily_full_scrape to finish.
Schedule: 03:00 UTC every day (1 h after scraping).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor

_DEFAULT_ARGS: dict = {
    "owner": "price_intelligence",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

_DBT_DIR = "/opt/airflow/dbt_project"
_DBT = f"cd {_DBT_DIR} && dbt"


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
        >> dbt_deps
        >> dbt_staging
        >> dbt_intermediate
        >> dbt_marts
        >> [dbt_test, dbt_docs]
    )
