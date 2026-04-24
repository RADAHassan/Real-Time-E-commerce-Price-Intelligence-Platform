"""
DAG: weekly_stats_report
Purpose : Execute the descriptive-stats and inferential-stats Jupyter notebooks
          via papermill, then convert the executed notebooks to HTML reports
          stored in analytics/reports/.
Schedule: Every Monday at 04:00 UTC.
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

_DEFAULT_ARGS: dict = {
    "owner": "price_intelligence",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}

_NOTEBOOKS_DIR = "/opt/airflow/analytics/notebooks"
_REPORTS_DIR = "/opt/airflow/analytics/reports"

# (task_id_suffix, notebook_stem)
_NOTEBOOKS = [
    ("descriptive_stats", "01_descriptive_stats"),
    ("inferential_stats", "02_inferential_stats"),
]


def _run_notebook(notebook_stem: str, **ctx) -> str:
    """Execute a notebook with papermill, inject run_date as a parameter."""
    import papermill as pm  # noqa: PLC0415

    run_date: str = ctx["ds"]  # YYYY-MM-DD supplied by Airflow
    input_nb = f"{_NOTEBOOKS_DIR}/{notebook_stem}.ipynb"
    output_nb = f"{_REPORTS_DIR}/{notebook_stem}_{run_date}.ipynb"

    os.makedirs(_REPORTS_DIR, exist_ok=True)
    pm.execute_notebook(
        input_path=input_nb,
        output_path=output_nb,
        parameters={"run_date": run_date},
        kernel_name="python3",
        progress_bar=False,
    )
    print(f"Executed notebook → {output_nb}")
    return output_nb


def _publish_html_reports(**ctx) -> None:
    """Convert every executed notebook for this run_date to HTML."""
    run_date: str = ctx["ds"]
    for _, stem in _NOTEBOOKS:
        executed = Path(f"{_REPORTS_DIR}/{stem}_{run_date}.ipynb")
        if not executed.exists():
            print(f"WARN: {executed} not found — skipping HTML conversion")
            continue
        subprocess.run(
            [
                "jupyter", "nbconvert", "--to", "html",
                str(executed), "--output-dir", _REPORTS_DIR,
            ],
            check=True,
        )
        print(f"HTML report → {_REPORTS_DIR}/{stem}_{run_date}.html")


with DAG(
    dag_id="weekly_stats_report",
    default_args=_DEFAULT_ARGS,
    description="Run descriptive + inferential notebooks via papermill → HTML reports",
    schedule_interval="0 4 * * 1",  # every Monday 04:00 UTC
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["analytics", "reporting", "phase4"],
    max_active_runs=1,
    doc_md=__doc__,
) as dag:

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    notebook_tasks = [
        PythonOperator(
            task_id=f"run_{suffix}",
            python_callable=_run_notebook,
            op_kwargs={"notebook_stem": stem},
        )
        for suffix, stem in _NOTEBOOKS
    ]

    publish = PythonOperator(
        task_id="publish_html_reports",
        python_callable=_publish_html_reports,
    )

    start >> notebook_tasks
    for t in notebook_tasks:
        t >> publish
    publish >> end
