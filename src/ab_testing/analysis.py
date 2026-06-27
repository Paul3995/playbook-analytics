"""
A/B test statistical analysis.
Supports:
  - Two-proportion z-test (conversion metrics)
  - Welch's t-test (continuous metrics: revenue, bet count)
  - Mann-Whitney U test (non-parametric fallback)
"""

from dataclasses import dataclass
from typing import Literal
import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class TestResult:
    experiment_name:  str
    metric:           str
    test_type:        str
    control_n:        int
    treatment_n:      int
    control_mean:     float
    treatment_mean:   float
    relative_lift:    float           # (treatment - control) / control
    p_value:          float
    statistic:        float
    confidence_level: float
    is_significant:   bool
    ci_lower:         float           # 95 % CI on the difference
    ci_upper:         float


def analyse(
    data: pd.DataFrame,
    experiment_name: str,
    metric: str,
    alpha: float = 0.05,
    test_type: Literal["auto", "proportion", "continuous", "nonparametric"] = "auto",
) -> TestResult:
    """
    data must have columns: variant ('control' | 'treatment'), metric_value (numeric)
    """
    ctrl = data[data["variant"] == "control"]["metric_value"].astype(float).values
    trt  = data[data["variant"] == "treatment"]["metric_value"].astype(float).values

    if len(ctrl) == 0 or len(trt) == 0:
        raise ValueError("Both variants must have observations")

    ctrl_mean = float(np.mean(ctrl))
    trt_mean  = float(np.mean(trt))
    lift      = (trt_mean - ctrl_mean) / ctrl_mean if ctrl_mean != 0 else 0.0

    # auto-detect test type from the data
    if test_type == "auto":
        unique_values = np.unique(np.concatenate([ctrl, trt]))
        is_binary = set(unique_values.tolist()).issubset({0.0, 1.0})
        test_type = "proportion" if is_binary else "continuous"

    if test_type == "proportion":
        stat, p_val, ci_lo, ci_hi = _proportion_test(ctrl, trt, alpha)
        ttype_label = "two-proportion z-test"
    elif test_type == "continuous":
        stat, p_val, ci_lo, ci_hi = _welch_t_test(ctrl, trt, alpha)
        ttype_label = "Welch's t-test"
    else:
        stat, p_val, ci_lo, ci_hi = _mann_whitney(ctrl, trt, alpha)
        ttype_label = "Mann-Whitney U"

    return TestResult(
        experiment_name  = experiment_name,
        metric           = metric,
        test_type        = ttype_label,
        control_n        = len(ctrl),
        treatment_n      = len(trt),
        control_mean     = round(ctrl_mean, 4),
        treatment_mean   = round(trt_mean, 4),
        relative_lift    = round(lift * 100, 2),     # as %
        p_value          = round(float(p_val), 4),
        statistic        = round(float(stat), 4),
        confidence_level = (1 - alpha) * 100,
        is_significant   = bool(p_val < alpha),
        ci_lower         = round(float(ci_lo), 4),
        ci_upper         = round(float(ci_hi), 4),
    )


def _proportion_test(
    ctrl: np.ndarray, trt: np.ndarray, alpha: float
) -> tuple[float, float, float, float]:
    n1, n2   = len(ctrl), len(trt)
    p1, p2   = ctrl.mean(), trt.mean()
    p_pool   = (ctrl.sum() + trt.sum()) / (n1 + n2)
    se_pool  = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    z        = (p2 - p1) / se_pool if se_pool > 0 else 0.0
    p_val    = 2 * (1 - stats.norm.cdf(abs(z)))

    se_diff  = np.sqrt(p1*(1-p1)/n1 + p2*(1-p2)/n2)
    z_crit   = stats.norm.ppf(1 - alpha/2)
    diff     = p2 - p1
    return z, p_val, diff - z_crit*se_diff, diff + z_crit*se_diff


def _welch_t_test(
    ctrl: np.ndarray, trt: np.ndarray, alpha: float
) -> tuple[float, float, float, float]:
    t, p_val = stats.ttest_ind(trt, ctrl, equal_var=False)
    n1, n2   = len(ctrl), len(trt)
    s1, s2   = ctrl.std(ddof=1), trt.std(ddof=1)
    se       = np.sqrt(s1**2/n1 + s2**2/n2)
    df       = (s1**2/n1 + s2**2/n2)**2 / (
                (s1**2/n1)**2/(n1-1) + (s2**2/n2)**2/(n2-1))
    t_crit   = stats.t.ppf(1 - alpha/2, df)
    diff     = trt.mean() - ctrl.mean()
    return float(t), float(p_val), diff - t_crit*se, diff + t_crit*se


def _mann_whitney(
    ctrl: np.ndarray, trt: np.ndarray, alpha: float
) -> tuple[float, float, float, float]:
    u, p_val = stats.mannwhitneyu(trt, ctrl, alternative="two-sided")
    # CI on median difference via bootstrap
    rng      = np.random.default_rng(0)
    diffs    = []
    for _ in range(1_000):
        bc   = rng.choice(ctrl, size=len(ctrl), replace=True)
        bt   = rng.choice(trt,  size=len(trt),  replace=True)
        diffs.append(np.median(bt) - np.median(bc))
    ci_lo, ci_hi = np.percentile(diffs, [alpha/2*100, (1-alpha/2)*100])
    return float(u), float(p_val), ci_lo, ci_hi


def summary_table(results: list[TestResult]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Experiment":      r.experiment_name,
            "Metric":          r.metric,
            "Test":            r.test_type,
            "Control n":       r.control_n,
            "Treatment n":     r.treatment_n,
            "Control mean":    r.control_mean,
            "Treatment mean":  r.treatment_mean,
            "Lift %":          r.relative_lift,
            "p-value":         r.p_value,
            f"CI {r.confidence_level:.0f}%": f"[{r.ci_lower}, {r.ci_upper}]",
            "Significant":     "YES" if r.is_significant else "no",
        }
        for r in results
    ])
