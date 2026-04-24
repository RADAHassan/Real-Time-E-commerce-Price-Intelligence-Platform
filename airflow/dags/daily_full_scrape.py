"""
DAG: daily_full_scrape
Purpose : Scrape all 5 target sites in parallel then verify that data landed
          in Bigtable (sanity check — not a full row count).
Schedule: 02:00 UTC every day.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

try:
    from scrapy_operator import ScrapyOperator  # loaded from plugins/ by Airflow
except ImportError:  # pragma: no cover — only missing outside the Airflow container
    from airflow.operators.bash import BashOperator as _Bash  # type: ignore[assignment]

    def ScrapyOperator(  # type: ignore[misc]
        *, spider: str, project_dir: str = "/opt/airflow",
        extra_settings: dict | None = None, **kw
    ):
        flags = " ".join(f"-s {k}={v}" for k, v in (extra_settings or {}).items())
        return _Bash(bash_command=f"cd {project_dir} && scrapy crawl {spider} {flags}".strip(), **kw)


_DEFAULT_ARGS: dict = {
    "owner": "price_intelligence",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

# (spider_name, human label) — order doesn't matter, tasks run in parallel
_SPIDERS = [
    ("books_spider",      "books.toscrape.com"),
    ("scrapeme_spider",   "scrapeme.live"),
    ("jumia_spider",      "jumia.ma"),
    ("ultrapc_spider",    "ultrapc.ma"),
    ("micromagma_spider", "micromagma.ma"),
]


def _verify_bigtable(**ctx) -> None:
    """Confirm at least one row exists in Bigtable after scraping."""
    import os
    import sys

    sys.path.insert(0, "/opt/airflow")
    from bigtable.client import BigtableClient  # noqa: PLC0415

    client = BigtableClient(
        project_id=os.environ["GCP_PROJECT_ID"],
        instance_id=os.environ.get("BIGTABLE_INSTANCE_ID", "price-intelligence"),
    )
    rows = list(client._table.read_rows(limit=1))
    if not rows:
        raise RuntimeError("Bigtable sanity check failed — no rows found after scraping")
    print(f"Bigtable OK — at least {len(rows)} row(s) present")


with DAG(
    dag_id="daily_full_scrape",
    default_args=_DEFAULT_ARGS,
    description="Scrape all 5 target sites in parallel → Bigtable",
    schedule_interval="0 2 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["scraping", "bigtable", "phase4"],
    max_active_runs=1,
    doc_md=__doc__,
) as dag:

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    scrape_tasks = [
        ScrapyOperator(
            task_id=f"scrape_{spider}",
            spider=spider,
            project_dir="/opt/airflow",
            extra_settings={"LOG_LEVEL": "WARNING", "BIGTABLE_PUSH_ENABLED": "true"},
        )
        for spider, _ in _SPIDERS
    ]

    verify = PythonOperator(
        task_id="verify_bigtable_count",
        python_callable=_verify_bigtable,
    )

    start >> scrape_tasks
    for t in scrape_tasks:
        t >> verify
    verify >> end
