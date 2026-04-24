"""
ScrapyOperator — thin BashOperator wrapper that runs a Scrapy spider.
Loaded automatically by Airflow from the plugins/ directory.
"""
from __future__ import annotations

from airflow.operators.bash import BashOperator


class ScrapyOperator(BashOperator):
    """
    Runs a Scrapy spider via the CLI.

    :param spider:       Spider name (e.g. "books_spider")
    :param project_dir:  Directory that contains scrapy.cfg (default: /opt/airflow)
    :param extra_settings: Mapping of -s KEY=VALUE overrides passed to scrapy
    """

    template_fields = (*BashOperator.template_fields, "spider")

    def __init__(
        self,
        *,
        spider: str,
        project_dir: str = "/opt/airflow",
        extra_settings: dict[str, str] | None = None,
        **kwargs,
    ) -> None:
        flags = " ".join(f"-s {k}={v}" for k, v in (extra_settings or {}).items())
        bash_command = f"cd {project_dir} && scrapy crawl {spider} {flags}".strip()
        super().__init__(bash_command=bash_command, **kwargs)
        self.spider = spider
