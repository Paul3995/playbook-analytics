"""
Transform layer — enriches raw tables and builds analytical views in DuckDB.
All transforms are idempotent (CREATE OR REPLACE VIEW).
"""

import duckdb
import logging

log = logging.getLogger(__name__)


def run_all(conn: duckdb.DuckDBPyConnection) -> None:
    _settled_bets_view(conn)
    _daily_ggr_view(conn)
    _player_activity_view(conn)
    _rfm_view(conn)
    _funnel_view(conn)
    log.info("all transform views created")


def _settled_bets_view(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE OR REPLACE VIEW v_settled_bets AS
        SELECT
            b.bet_id,
            b.user_id,
            b.bet_type,
            b.stake,
            b.actual_payout,
            COALESCE(b.actual_payout, 0)    AS payout,
            b.stake - COALESCE(b.actual_payout, 0) AS ggr_contribution,
            b.status,
            b.placed_ts::TIMESTAMP           AS placed_ts,
            b.settled_ts::TIMESTAMP          AS settled_ts,
            b.currency,
            u.country_code,
            u.vip_tier
        FROM bets b
        JOIN users u ON u.user_id = b.user_id
        WHERE b.status IN ('won', 'lost')
    """)
    log.debug("view created: v_settled_bets")


def _daily_ggr_view(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE OR REPLACE VIEW v_daily_ggr AS
        SELECT
            settled_ts::DATE                            AS settlement_date,
            currency,
            COUNT(*)                                    AS settled_bets,
            ROUND(SUM(stake), 2)                        AS total_stakes,
            ROUND(SUM(payout), 2)                       AS total_payouts,
            ROUND(SUM(ggr_contribution), 2)             AS ggr,
            ROUND(SUM(ggr_contribution) / NULLIF(SUM(stake), 0) * 100, 2) AS hold_pct
        FROM v_settled_bets
        GROUP BY settled_ts::DATE, currency
    """)
    log.debug("view created: v_daily_ggr")


def _player_activity_view(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE OR REPLACE VIEW v_player_activity AS
        SELECT
            b.user_id,
            b.placed_ts::DATE                           AS activity_date,
            COUNT(b.bet_id)                             AS bets_placed,
            SUM(b.stake)                                AS total_staked
        FROM bets b
        GROUP BY b.user_id, b.placed_ts::DATE
    """)
    log.debug("view created: v_player_activity")


def _rfm_view(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE OR REPLACE VIEW v_rfm AS
        WITH base AS (
            SELECT
                user_id,
                MAX(placed_ts::DATE)                    AS last_bet_date,
                COUNT(bet_id)                           AS frequency,
                SUM(stake)                              AS monetary
            FROM bets
            GROUP BY user_id
        )
        SELECT
            user_id,
            last_bet_date,
            frequency,
            ROUND(monetary, 2)                          AS monetary,
            NTILE(5) OVER (ORDER BY last_bet_date DESC) AS r_score,
            NTILE(5) OVER (ORDER BY frequency DESC)     AS f_score,
            NTILE(5) OVER (ORDER BY monetary DESC)      AS m_score
        FROM base
    """)
    log.debug("view created: v_rfm")


def _funnel_view(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE OR REPLACE VIEW v_acquisition_funnel AS
        SELECT
            u.registration_ts::DATE     AS reg_date,
            COUNT(DISTINCT u.user_id)   AS registrations,
            COUNT(DISTINCT CASE WHEN t.type = 'deposit' AND t.status = 'completed'
                                THEN t.user_id END) AS first_depositors,
            COUNT(DISTINCT CASE WHEN b.bet_id IS NOT NULL
                                THEN b.user_id END) AS first_bettors
        FROM users u
        LEFT JOIN transactions t ON t.user_id = u.user_id
        LEFT JOIN bets b         ON b.user_id  = u.user_id
        GROUP BY u.registration_ts::DATE
    """)
    log.debug("view created: v_acquisition_funnel")
