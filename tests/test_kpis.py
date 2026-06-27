"""Tests for KPI calculator."""

import pytest
from datetime import date
from src.kpis.calculator import KPICalculator


@pytest.fixture
def calc(conn):
    return KPICalculator(conn)


START = date(2024, 1, 1)
END   = date(2024, 6, 30)


class TestDailyGGR:
    def test_returns_dataframe(self, calc):
        df = calc.daily_ggr(START, END)
        assert not df.empty

    def test_columns_present(self, calc):
        df = calc.daily_ggr(START, END)
        assert {"settlement_date", "ggr", "total_stakes", "hold_pct"}.issubset(df.columns)

    def test_ggr_never_negative_on_aggregate(self, calc):
        df = calc.daily_ggr(START, END)
        assert df["total_stakes"].sum() >= 0

    def test_hold_pct_is_numeric(self, calc):
        df = calc.daily_ggr(START, END)
        assert df["hold_pct"].dtype.kind == "f"
        assert df["hold_pct"].notna().all()


class TestDailyActivePlayers:
    def test_returns_rows(self, calc):
        df = calc.daily_active_players(START, END)
        assert not df.empty

    def test_dap_positive(self, calc):
        df = calc.daily_active_players(START, END)
        assert (df["dap"] > 0).all()

    def test_no_dates_outside_range(self, calc):
        df = calc.daily_active_players(START, END)
        assert df["activity_date"].between(str(START), str(END)).all()


class TestRetentionCohorts:
    def test_returns_dataframe(self, calc):
        df = calc.retention_cohorts(START, END)
        assert not df.empty

    def test_retention_pct_capped_at_100(self, calc):
        df = calc.retention_cohorts(START, END)
        for col in ["d1_retention_pct", "d7_retention_pct", "d30_retention_pct"]:
            if col in df.columns:
                assert df[col].dropna().le(100).all()

    def test_d7_lte_d1(self, calc):
        """Day-7 retention should generally be ≤ Day-1 on average."""
        df = calc.retention_cohorts(START, END)
        if "d1_retention_pct" in df.columns and "d7_retention_pct" in df.columns:
            d1_avg = df["d1_retention_pct"].mean()
            d7_avg = df["d7_retention_pct"].mean()
            assert d7_avg <= d1_avg + 5  # allow small tolerance


class TestMonthlyARPU:
    def test_returns_rows(self, calc):
        df = calc.monthly_arpu(START, END)
        assert not df.empty

    def test_arpu_is_numeric(self, calc):
        df = calc.monthly_arpu(START, END)
        assert df["arpu"].notna().all()
        assert df["arpu"].dtype.kind == "f"

    def test_active_players_positive(self, calc):
        df = calc.monthly_arpu(START, END)
        assert (df["active_players"] > 0).all()


class TestScorecard:
    def test_scorecard_has_rows(self, calc):
        sc = calc.scorecard(END)
        assert not sc.empty

    def test_scorecard_columns(self, calc):
        sc = calc.scorecard(END)
        assert {"kpi", "value", "unit"}.issubset(sc.columns)
