"""Tests for data quality checks."""

import pytest
from src.quality.checks import DataQualityRunner


class TestDataQualityRunner:
    def test_all_checks_pass_on_clean_data(self, conn):
        runner  = DataQualityRunner(conn)
        results = runner.run(raise_on_failure=False)
        failed  = [r for r in results if not r.passed]
        assert failed == [], f"Unexpected failures: {[r.check for r in failed]}"

    def test_expected_check_names_present(self, conn):
        runner    = DataQualityRunner(conn)
        results   = runner.run(raise_on_failure=False)
        names     = {r.check for r in results}
        expected  = {
            "no_null_user_ids",
            "no_orphan_bets",
            "no_negative_stakes",
            "no_future_settled_dates",
            "stake_vs_payout_consistency",
            "no_duplicate_bets",
            "selection_odds_range",
            "experiment_variant_balance",
        }
        assert expected.issubset(names)

    def test_results_have_details(self, conn):
        runner  = DataQualityRunner(conn)
        results = runner.run(raise_on_failure=False)
        for r in results:
            assert r.details, f"Check {r.check} has empty details"
