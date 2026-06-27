"""Tests for A/B testing modules."""

import numpy as np
import pytest
from src.ab_testing.analysis import analyse, summary_table
from src.ab_testing.experiment import ExperimentManager, ExperimentConfig, required_sample_size


# ── Unit tests: statistical functions ─────────────────────────────────────────

class TestProportionTest:
    def _make_data(self, ctrl_rate, trt_rate, n=1000):
        import pandas as pd
        rng  = np.random.default_rng(0)
        ctrl = pd.DataFrame({
            "variant":      ["control"]   * n,
            "metric_value": rng.binomial(1, ctrl_rate, n).astype(float),
        })
        trt  = pd.DataFrame({
            "variant":      ["treatment"] * n,
            "metric_value": rng.binomial(1, trt_rate,  n).astype(float),
        })
        import pandas as pd
        return pd.concat([ctrl, trt], ignore_index=True)

    def test_no_effect_is_not_significant(self):
        data   = self._make_data(0.30, 0.30)
        result = analyse(data, "exp", "metric", alpha=0.05)
        assert not result.is_significant

    def test_large_effect_is_significant(self):
        data   = self._make_data(0.10, 0.30, n=2000)
        result = analyse(data, "exp", "metric", alpha=0.05)
        assert result.is_significant

    def test_lift_direction_correct(self):
        data   = self._make_data(0.20, 0.30, n=5000)
        result = analyse(data, "exp", "metric")
        assert result.relative_lift > 0

    def test_negative_lift_detected(self):
        data   = self._make_data(0.30, 0.10, n=5000)
        result = analyse(data, "exp", "metric")
        assert result.relative_lift < 0

    def test_ci_contains_zero_when_not_significant(self):
        data   = self._make_data(0.25, 0.26, n=200)
        result = analyse(data, "exp", "metric")
        if not result.is_significant:
            assert result.ci_lower <= 0 <= result.ci_upper

    def test_p_value_between_0_and_1(self):
        data   = self._make_data(0.20, 0.25)
        result = analyse(data, "exp", "metric")
        assert 0 <= result.p_value <= 1


class TestContinuousTest:
    def _make_continuous(self, ctrl_mean, trt_mean, n=500, std=10.0):
        import pandas as pd
        rng = np.random.default_rng(1)
        return pd.DataFrame({
            "variant":      ["control"] * n + ["treatment"] * n,
            "metric_value": np.concatenate([
                rng.normal(ctrl_mean, std, n),
                rng.normal(trt_mean,  std, n),
            ]),
        })

    def test_same_mean_not_significant(self):
        data   = self._make_continuous(50, 50)
        result = analyse(data, "exp", "revenue", test_type="continuous")
        assert not result.is_significant

    def test_different_means_significant(self):
        data   = self._make_continuous(50, 70, n=1000, std=5.0)
        result = analyse(data, "exp", "revenue", test_type="continuous")
        assert result.is_significant


class TestSampleSize:
    def test_larger_effect_needs_fewer_samples(self):
        small = ExperimentConfig("e1","m",0.10, min_detectable=0.05)
        large = ExperimentConfig("e1","m",0.10, min_detectable=0.20)
        assert required_sample_size(small) > required_sample_size(large)

    def test_higher_power_needs_more_samples(self):
        low  = ExperimentConfig("e1","m",0.20, min_detectable=0.10, power=0.70)
        high = ExperimentConfig("e1","m",0.20, min_detectable=0.10, power=0.90)
        assert required_sample_size(high) > required_sample_size(low)

    def test_returns_positive_integer(self):
        cfg = ExperimentConfig("e1","m",0.30, min_detectable=0.10)
        n   = required_sample_size(cfg)
        assert isinstance(n, int) and n > 0


class TestSummaryTable:
    def test_summary_table_shape(self):
        import pandas as pd
        ctrl = pd.DataFrame({"variant": ["control"]*200,   "metric_value": [0.0]*100 + [1.0]*100})
        trt  = pd.DataFrame({"variant": ["treatment"]*200, "metric_value": [0.0]*80  + [1.0]*120})
        data = pd.concat([ctrl, trt])
        r    = analyse(data, "test_exp", "conversion")
        tbl  = summary_table([r])
        assert len(tbl) == 1
        assert "Experiment" in tbl.columns


# ── Integration tests: ExperimentManager ──────────────────────────────────────

class TestExperimentManager:
    def test_list_experiments_not_empty(self, conn):
        mgr = ExperimentManager(conn)
        df  = mgr.list_experiments()
        assert not df.empty

    def test_variant_sizes_equal_ish(self, conn):
        mgr = ExperimentManager(conn)
        df  = mgr.variant_sizes(1)
        assert set(df["variant"].tolist()) == {"control", "treatment"}
        sizes = df.set_index("variant")["n"]
        ratio = min(sizes) / max(sizes)
        assert ratio >= 0.75   # within 25% of each other

    def test_get_metric_data_returns_both_variants(self, conn):
        mgr  = ExperimentManager(conn)
        data = mgr.get_metric_data(1, "first_deposit_rate")
        assert set(data["variant"].unique()) == {"control", "treatment"}

    def test_metric_values_are_binary_for_conversion(self, conn):
        mgr  = ExperimentManager(conn)
        data = mgr.get_metric_data(1, "first_deposit_rate")
        assert set(data["metric_value"].unique()).issubset({0, 1, 0.0, 1.0})
