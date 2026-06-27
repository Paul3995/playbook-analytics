"""
Airflow DAG: weekly_report
Runs every Monday at 08:00 UTC.
Generates a weekly KPI report (GGR, retention, ARPU, RFM summary)
and logs it — in production this would email stakeholders or push to Metabase.
"""

from __future__ import annotations

from datetime import datetime, timedelta, date
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator

log = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner":            "data-analytics",
    "retries":          1,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": True,
    "email":            ["data-team@playbook.io"],
}


def task_weekly_ggr(**ctx) -> None:
    import duckdb
    from src.kpis.calculator import KPICalculator

    ds      = date.fromisoformat(ctx["ds"])
    start   = ds - timedelta(days=7)
    conn    = duckdb.connect("playbook.duckdb")
    calc    = KPICalculator(conn)
    ggr_df  = calc.daily_ggr(start, ds)

    log.info("=== Weekly GGR Report (%s to %s) ===", start, ds)
    log.info("Total GGR: %.2f", ggr_df["ggr"].sum())
    log.info("Avg Hold %%: %.2f", ggr_df["hold_pct"].mean())
    log.info("Detail:\n%s", ggr_df.to_string(index=False))
    conn.close()


def task_weekly_retention(**ctx) -> None:
    import duckdb
    from src.kpis.calculator import KPICalculator

    ds    = date.fromisoformat(ctx["ds"])
    start = ds - timedelta(days=60)      # cohorts from prior 60 days
    conn  = duckdb.connect("playbook.duckdb")
    calc  = KPICalculator(conn)
    df    = calc.retention_cohorts(start, ds)

    log.info("=== Retention Cohorts (%s to %s) ===", start, ds)
    log.info(df.tail(10).to_string(index=False))
    conn.close()


def task_weekly_arpu(**ctx) -> None:
    import duckdb
    from src.kpis.calculator import KPICalculator

    ds    = date.fromisoformat(ctx["ds"])
    start = ds - timedelta(days=90)
    conn  = duckdb.connect("playbook.duckdb")
    calc  = KPICalculator(conn)
    df    = calc.monthly_arpu(start, ds)

    log.info("=== Monthly ARPU ===")
    log.info(df.to_string(index=False))
    conn.close()


def task_rfm_summary(**ctx) -> None:
    import duckdb

    conn = duckdb.connect("playbook.duckdb")
    df   = conn.execute("""
        SELECT
            CASE
                WHEN (r_score + f_score + m_score) >= 13 THEN 'Champions'
                WHEN (r_score + f_score + m_score) >= 10 THEN 'Loyal'
                WHEN r_score >= 4 AND f_score >= 3       THEN 'Potential'
                WHEN r_score >= 4                        THEN 'New'
                WHEN r_score <= 2 AND f_score >= 4       THEN 'At Risk'
                WHEN r_score <= 2 AND f_score <= 2       THEN 'Churned'
                ELSE 'Occasional'
            END                         AS segment,
            COUNT(*)                    AS players,
            ROUND(AVG(monetary), 2)     AS avg_spend
        FROM mart_player_rfm
        GROUP BY segment
        ORDER BY avg_spend DESC
    """).df()
    log.info("=== RFM Segments ===\n%s", df.to_string(index=False))
    conn.close()


with DAG(
    dag_id          = "weekly_report",
    description     = "Monday morning: GGR summary, retention, ARPU, RFM segments",
    schedule        = "0 8 * * 1",
    start_date      = datetime(2024, 1, 1),
    catchup         = False,
    default_args    = DEFAULT_ARGS,
    tags            = ["report", "weekly"],
) as dag:

    ggr       = PythonOperator(task_id="weekly_ggr",       python_callable=task_weekly_ggr)
    retention = PythonOperator(task_id="weekly_retention", python_callable=task_weekly_retention)
    arpu      = PythonOperator(task_id="weekly_arpu",      python_callable=task_weekly_arpu)
    rfm       = PythonOperator(task_id="rfm_summary",      python_callable=task_rfm_summary)

    [ggr, retention, arpu] >> rfm
