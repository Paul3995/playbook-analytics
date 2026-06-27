"""
KPI calculator — runs SQL/Python computations against DuckDB and returns
structured results that can be fed to a dashboard or report.
"""

import duckdb
import pandas as pd
from datetime import date, timedelta
from .definitions import REGISTRY, KPI


class KPICalculator:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    # ── Revenue ───────────────────────────────────────────────────────────────

    def daily_ggr(self, start: date, end: date) -> pd.DataFrame:
        return self.conn.execute("""
            SELECT
                settlement_date,
                currency,
                settled_bets,
                total_stakes,
                total_payouts,
                ggr,
                hold_pct
            FROM v_daily_ggr
            WHERE settlement_date BETWEEN ? AND ?
            ORDER BY settlement_date, currency
        """, [start, end]).df()

    def monthly_arpu(self, start: date, end: date) -> pd.DataFrame:
        return self.conn.execute("""
            WITH monthly_ggr AS (
                SELECT
                    strftime(settled_ts::DATE, '%Y-%m')     AS yr_month,
                    SUM(ggr_contribution)                   AS total_ggr
                FROM v_settled_bets
                WHERE settled_ts::DATE BETWEEN ? AND ?
                GROUP BY strftime(settled_ts::DATE, '%Y-%m')
            ),
            monthly_active AS (
                SELECT
                    strftime(placed_ts::DATE, '%Y-%m')      AS yr_month,
                    COUNT(DISTINCT user_id)                  AS active_players
                FROM bets
                WHERE placed_ts::DATE BETWEEN ? AND ?
                GROUP BY strftime(placed_ts::DATE, '%Y-%m')
            )
            SELECT
                g.yr_month,
                ma.active_players,
                ROUND(g.total_ggr, 2)                       AS total_ggr,
                ROUND(g.total_ggr / ma.active_players, 2)   AS arpu
            FROM monthly_ggr g
            JOIN monthly_active ma ON ma.yr_month = g.yr_month
            ORDER BY g.yr_month DESC
        """, [start, end, start, end]).df()

    # ── Engagement ────────────────────────────────────────────────────────────

    def daily_active_players(self, start: date, end: date) -> pd.DataFrame:
        return self.conn.execute("""
            SELECT
                placed_ts::DATE             AS activity_date,
                COUNT(DISTINCT user_id)     AS dap
            FROM bets
            WHERE placed_ts::DATE BETWEEN ? AND ?
            GROUP BY placed_ts::DATE
            ORDER BY activity_date
        """, [start, end]).df()

    # ── Retention cohorts ─────────────────────────────────────────────────────

    def retention_cohorts(self, start: date, end: date) -> pd.DataFrame:
        return self.conn.execute("""
            WITH first_bet AS (
                SELECT user_id, MIN(placed_ts::DATE) AS cohort_date
                FROM bets
                WHERE placed_ts::DATE BETWEEN ? AND ?
                GROUP BY user_id
            ),
            activity AS (
                SELECT DISTINCT user_id, placed_ts::DATE AS activity_date
                FROM bets
            ),
            pairs AS (
                SELECT
                    f.cohort_date,
                    f.user_id,
                    (a.activity_date - f.cohort_date)   AS days_since
                FROM first_bet f
                JOIN activity a ON a.user_id = f.user_id
            )
            SELECT
                cohort_date,
                COUNT(DISTINCT CASE WHEN days_since = 0  THEN user_id END) AS cohort_size,
                COUNT(DISTINCT CASE WHEN days_since = 1  THEN user_id END) AS retained_d1,
                COUNT(DISTINCT CASE WHEN days_since = 7  THEN user_id END) AS retained_d7,
                COUNT(DISTINCT CASE WHEN days_since = 30 THEN user_id END) AS retained_d30,
                ROUND(
                    COUNT(DISTINCT CASE WHEN days_since = 1 THEN user_id END) * 100.0
                    / NULLIF(COUNT(DISTINCT CASE WHEN days_since = 0 THEN user_id END), 0), 1
                ) AS d1_retention_pct,
                ROUND(
                    COUNT(DISTINCT CASE WHEN days_since = 7 THEN user_id END) * 100.0
                    / NULLIF(COUNT(DISTINCT CASE WHEN days_since = 0 THEN user_id END), 0), 1
                ) AS d7_retention_pct,
                ROUND(
                    COUNT(DISTINCT CASE WHEN days_since = 30 THEN user_id END) * 100.0
                    / NULLIF(COUNT(DISTINCT CASE WHEN days_since = 0 THEN user_id END), 0), 1
                ) AS d30_retention_pct
            FROM pairs
            GROUP BY cohort_date
            ORDER BY cohort_date
        """, [start, end]).df()

    # ── Acquisition funnel ────────────────────────────────────────────────────

    def acquisition_funnel(self, start: date, end: date) -> pd.DataFrame:
        return self.conn.execute("""
            SELECT *
            FROM v_acquisition_funnel
            WHERE reg_date BETWEEN ? AND ?
            ORDER BY reg_date
        """, [start, end]).df()

    # ── Scorecard ─────────────────────────────────────────────────────────────

    def scorecard(self, as_of: date) -> pd.DataFrame:
        """Single-row KPI scorecard for the trailing 30 days up to as_of."""
        start = as_of - timedelta(days=30)
        rows = []
        ggr_df = self.daily_ggr(start, as_of)
        if not ggr_df.empty:
            total_ggr  = ggr_df["ggr"].sum()
            total_st   = ggr_df["total_stakes"].sum()
            hold       = round(total_ggr / total_st * 100, 2) if total_st else 0

            dap_df = self.daily_active_players(start, as_of)
            avg_dap = round(dap_df["dap"].mean(), 0) if not dap_df.empty else 0

            rows = [
                {"kpi": "GGR (30d)",   "value": round(total_ggr, 2), "unit": "currency", "target": None},
                {"kpi": "Hold %",      "value": hold,                 "unit": "pct",      "target": REGISTRY["hold_pct"].target},
                {"kpi": "Avg DAP",     "value": avg_dap,              "unit": "count",    "target": None},
            ]
        return pd.DataFrame(rows)
