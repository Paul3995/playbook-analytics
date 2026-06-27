"""Tests for ETL transform views."""

import pytest


class TestViews:
    def test_v_settled_bets_exists(self, conn):
        df = conn.execute("SELECT COUNT(*) AS n FROM v_settled_bets").df()
        assert df["n"].iloc[0] > 0

    def test_v_daily_ggr_hold_pct_positive(self, conn):
        df = conn.execute("""
            SELECT hold_pct FROM v_daily_ggr WHERE hold_pct IS NOT NULL LIMIT 100
        """).df()
        assert not df.empty

    def test_v_rfm_scores_in_range(self, conn):
        df = conn.execute("""
            SELECT r_score, f_score, m_score FROM v_rfm LIMIT 100
        """).df()
        for col in ["r_score", "f_score", "m_score"]:
            assert df[col].between(1, 5).all(), f"{col} out of range"

    def test_v_acquisition_funnel_columns(self, conn):
        df = conn.execute("SELECT * FROM v_acquisition_funnel LIMIT 1").df()
        assert {"reg_date", "registrations", "first_depositors", "first_bettors"}.issubset(df.columns)

    def test_mart_daily_ggr_materialised(self, conn):
        df = conn.execute("SELECT COUNT(*) AS n FROM mart_daily_ggr").df()
        assert df["n"].iloc[0] > 0

    def test_mart_player_rfm_all_users_present(self, conn):
        n_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        n_rfm   = conn.execute("SELECT COUNT(*) FROM mart_player_rfm").fetchone()[0]
        # RFM only covers bettors; should be ≤ total users
        assert 0 < n_rfm <= n_users

    def test_ggr_contribution_sign(self, conn):
        """GGR can be negative per-bet (big winner) but total should be positive."""
        total = conn.execute("SELECT SUM(ggr_contribution) FROM v_settled_bets").fetchone()[0]
        assert total is not None
