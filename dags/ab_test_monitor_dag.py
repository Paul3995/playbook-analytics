"""
Airflow DAG: ab_test_monitor
Runs every 6 hours.
For each running experiment, computes statistical results and logs findings.
Alerts when significance is reached so the team can act.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator

log = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner":            "data-analytics",
    "retries":          1,
    "retry_delay":      timedelta(minutes=2),
    "email_on_failure": True,
    "email":            ["data-team@playbook.io"],
}


def task_run_ab_checks(**ctx) -> None:
    import duckdb
    from src.ab_testing.experiment import ExperimentManager
    from src.ab_testing.analysis import analyse, summary_table

    conn    = duckdb.connect("playbook.duckdb")
    manager = ExperimentManager(conn)
    exps    = manager.list_experiments()
    running = exps[exps["status"] == "running"]

    results = []
    for _, exp in running.iterrows():
        exp_id  = int(exp["experiment_id"])
        metric  = exp["metric"]
        log.info("Analysing experiment %s (metric: %s)", exp["name"], metric)

        try:
            data   = manager.get_metric_data(exp_id, metric)
            result = analyse(data, exp["name"], metric)
            results.append(result)

            if result.is_significant:
                log.warning(
                    "SIGNIFICANT RESULT — %s: lift=%.1f%%, p=%.4f",
                    exp["name"], result.relative_lift, result.p_value,
                )
            else:
                log.info(
                    "Not yet significant — %s: lift=%.1f%%, p=%.4f",
                    exp["name"], result.relative_lift, result.p_value,
                )
        except Exception as exc:
            log.error("Failed to analyse %s: %s", exp["name"], exc)

    if results:
        table = summary_table(results)
        log.info("A/B Summary:\n%s", table.to_string(index=False))

    conn.close()


with DAG(
    dag_id          = "ab_test_monitor",
    description     = "Every 6 h: check all running A/B experiments for significance",
    schedule        = "0 */6 * * *",
    start_date      = datetime(2024, 1, 1),
    catchup         = False,
    default_args    = DEFAULT_ARGS,
    tags            = ["ab_test", "monitoring"],
) as dag:

    run_checks = PythonOperator(
        task_id         = "run_ab_checks",
        python_callable = task_run_ab_checks,
    )
