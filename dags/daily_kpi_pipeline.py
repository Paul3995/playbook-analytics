"""
Airflow DAG: daily_kpi_pipeline
Runs every day at 06:00 UTC.
Stages: extract → quality check → transform → load → scorecard alert
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator

log = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner":            "data-analytics",
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": True,
    "email":            ["data-team@playbook.io"],
}


def task_extract(**ctx) -> None:
    import duckdb
    from data.seeds.generate_data import main as generate
    from src.etl.extract import load_csvs_to_duckdb

    log.info("Running extract for ds=%s", ctx["ds"])
    generate()
    conn = duckdb.connect("playbook.duckdb")
    load_csvs_to_duckdb(conn, "data/seeds")
    conn.close()


def task_quality(**ctx) -> None:
    import duckdb
    from src.quality.checks import DataQualityRunner

    conn = duckdb.connect("playbook.duckdb")
    runner = DataQualityRunner(conn)
    results = runner.run(raise_on_failure=True)
    passes  = sum(1 for r in results if r.passed)
    log.info("Quality: %d/%d checks passed", passes, len(results))
    conn.close()


def task_transform(**ctx) -> None:
    import duckdb
    from src.etl.transform import run_all

    conn = duckdb.connect("playbook.duckdb")
    run_all(conn)
    conn.close()


def task_load(**ctx) -> None:
    import duckdb
    from src.etl.load import materialise_marts

    conn = duckdb.connect("playbook.duckdb")
    materialise_marts(conn)
    conn.close()


def task_scorecard(**ctx) -> None:
    import duckdb
    from datetime import date
    from src.kpis.calculator import KPICalculator

    conn = duckdb.connect("playbook.duckdb")
    calc = KPICalculator(conn)
    sc   = calc.scorecard(date.fromisoformat(ctx["ds"]))
    log.info("KPI Scorecard (trailing 30d):\n%s", sc.to_string(index=False))
    conn.close()


with DAG(
    dag_id          = "daily_kpi_pipeline",
    description     = "Daily extract → quality → transform → load → scorecard",
    schedule        = "0 6 * * *",
    start_date      = datetime(2024, 1, 1),
    catchup         = False,
    default_args    = DEFAULT_ARGS,
    tags            = ["kpi", "etl", "daily"],
) as dag:

    extract   = PythonOperator(task_id="extract",   python_callable=task_extract)
    quality   = PythonOperator(task_id="quality",   python_callable=task_quality)
    transform = PythonOperator(task_id="transform", python_callable=task_transform)
    load      = PythonOperator(task_id="load",      python_callable=task_load)
    scorecard = PythonOperator(task_id="scorecard", python_callable=task_scorecard)

    extract >> quality >> transform >> load >> scorecard
