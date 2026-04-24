"""
DAG integrity tests — verify each DAG file loads cleanly and has the expected
task structure.  Tests are skipped automatically when apache-airflow is not
installed (so `make test` in a plain venv always passes).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

try:
    from airflow import DAG as AirflowDAG  # noqa: E402
    from airflow.operators.bash import BashOperator as _probe  # noqa: F401
except (ImportError, AttributeError):
    pytest.skip("apache-airflow not installed", allow_module_level=True)

_DAGS_DIR = Path(__file__).parents[2] / "airflow" / "dags"
_DAG_FILES = sorted(_DAGS_DIR.glob("*.py"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_dag_module(dag_file: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(dag_file.stem, dag_file)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _dags_in(module: ModuleType) -> list[AirflowDAG]:
    return [v for v in vars(module).values() if isinstance(v, AirflowDAG)]


# ---------------------------------------------------------------------------
# Parametrised: every DAG file must import cleanly and expose ≥1 DAG
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _airflow_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AIRFLOW__CORE__UNIT_TEST_MODE", "True")
    monkeypatch.setenv("AIRFLOW_HOME", str(tmp_path))
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.setenv("BIGTABLE_INSTANCE_ID", "test-instance")


@pytest.mark.parametrize("dag_file", _DAG_FILES, ids=[f.stem for f in _DAG_FILES])
def test_dag_loads_without_error(dag_file: Path) -> None:
    module = _load_dag_module(dag_file)
    dags = _dags_in(module)
    assert dags, f"No DAG object found in {dag_file.name}"


# ---------------------------------------------------------------------------
# Structural tests per DAG
# ---------------------------------------------------------------------------

def test_daily_full_scrape_structure() -> None:
    module = _load_dag_module(_DAGS_DIR / "daily_full_scrape.py")
    dag: AirflowDAG = module.dag  # type: ignore[attr-defined]

    assert dag.schedule_interval == "0 2 * * *"
    task_ids = {t.task_id for t in dag.tasks}

    assert "start" in task_ids
    assert "end" in task_ids
    assert "verify_bigtable_count" in task_ids

    spider_tasks = [tid for tid in task_ids if tid.startswith("scrape_")]
    assert len(spider_tasks) == 5, f"Expected 5 scrape tasks, got {spider_tasks}"


def test_dbt_transformations_structure() -> None:
    module = _load_dag_module(_DAGS_DIR / "dbt_transformations.py")
    dag: AirflowDAG = module.dag  # type: ignore[attr-defined]

    assert dag.schedule_interval == "0 3 * * *"
    task_ids = {t.task_id for t in dag.tasks}

    for expected in [
        "wait_for_daily_scrape",
        "dbt_deps",
        "dbt_run_staging",
        "dbt_run_intermediate",
        "dbt_run_marts",
        "dbt_test",
        "dbt_docs_generate",
    ]:
        assert expected in task_ids, f"Missing task: {expected}"


def test_weekly_stats_report_structure() -> None:
    module = _load_dag_module(_DAGS_DIR / "weekly_stats_report.py")
    dag: AirflowDAG = module.dag  # type: ignore[attr-defined]

    assert dag.schedule_interval == "0 4 * * 1"
    task_ids = {t.task_id for t in dag.tasks}

    assert "start" in task_ids
    assert "end" in task_ids
    assert "publish_html_reports" in task_ids

    notebook_tasks = [tid for tid in task_ids if tid.startswith("run_")]
    assert len(notebook_tasks) == 2, f"Expected 2 notebook tasks, got {notebook_tasks}"


# ---------------------------------------------------------------------------
# Dependency / ordering checks
# ---------------------------------------------------------------------------

def test_daily_scrape_verify_depends_on_all_spiders() -> None:
    module = _load_dag_module(_DAGS_DIR / "daily_full_scrape.py")
    dag: AirflowDAG = module.dag  # type: ignore[attr-defined]

    verify = dag.get_task("verify_bigtable_count")
    upstream_ids = {t.task_id for t in verify.upstream_list}
    spider_tasks = {t.task_id for t in dag.tasks if t.task_id.startswith("scrape_")}
    assert spider_tasks.issubset(upstream_ids), (
        f"verify_bigtable_count is not downstream of all spiders: {spider_tasks - upstream_ids}"
    )


def test_dbt_layers_run_in_order() -> None:
    module = _load_dag_module(_DAGS_DIR / "dbt_transformations.py")
    dag: AirflowDAG = module.dag  # type: ignore[attr-defined]

    def upstream_ids(task_id: str) -> set[str]:
        return {t.task_id for t in dag.get_task(task_id).upstream_list}

    assert "dbt_run_staging" in upstream_ids("dbt_run_intermediate")
    assert "dbt_run_intermediate" in upstream_ids("dbt_run_marts")
    assert "dbt_run_marts" in upstream_ids("dbt_test")
    assert "dbt_run_marts" in upstream_ids("dbt_docs_generate")
