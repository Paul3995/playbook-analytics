"""
A/B Test experiment manager.
Handles variant assignment, sample size estimation, and result loading.
"""

import math
import duckdb
import pandas as pd
from dataclasses import dataclass


@dataclass
class ExperimentConfig:
    name:             str
    metric:           str
    baseline_rate:    float     # expected control conversion rate (0–1)
    min_detectable:   float     # minimum effect size to detect (relative, e.g. 0.10 = 10%)
    alpha:            float = 0.05
    power:            float = 0.80


def required_sample_size(config: ExperimentConfig) -> int:
    """
    Two-proportion z-test sample size per variant.
    Uses the Fleiss-formula approximation.
    """
    p1  = config.baseline_rate
    p2  = p1 * (1 + config.min_detectable)
    p_  = (p1 + p2) / 2

    z_alpha = _z(1 - config.alpha / 2)
    z_beta  = _z(config.power)

    numerator   = (z_alpha * math.sqrt(2 * p_ * (1 - p_))
                   + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    denominator = (p2 - p1) ** 2
    return math.ceil(numerator / denominator)


def _z(p: float) -> float:
    """Quantile of the standard normal (Abramowitz & Stegun approx)."""
    import math
    if p < 0.5:
        return -_z(1 - p)
    t = math.sqrt(-2 * math.log(1 - p))
    c = (2.515517, 0.802853, 0.010328)
    d = (1.432788, 0.189269, 0.001308)
    return t - (c[0] + c[1]*t + c[2]*t**2) / (1 + d[0]*t + d[1]*t**2 + d[2]*t**3)


class ExperimentManager:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def list_experiments(self) -> pd.DataFrame:
        return self.conn.execute("""
            SELECT
                experiment_id,
                name,
                metric,
                status,
                start_ts,
                end_ts,
                min_sample_size,
                (SELECT COUNT(*) FROM experiment_assignments ea
                 WHERE ea.experiment_id = e.experiment_id) AS total_assignments
            FROM experiments e
            ORDER BY experiment_id
        """).df()

    def variant_sizes(self, experiment_id: int) -> pd.DataFrame:
        return self.conn.execute("""
            SELECT
                variant,
                COUNT(*) AS n
            FROM experiment_assignments
            WHERE experiment_id = ?
            GROUP BY variant
        """, [experiment_id]).df()

    def get_metric_data(
        self, experiment_id: int, metric: str
    ) -> pd.DataFrame:
        """
        Returns per-user metric values for each variant.
        Supported metrics: 'first_deposit_rate', 'bet_count', 'ggr', 'accumulator_bet_rate'
        """
        if metric == "first_deposit_rate":
            query = """
                SELECT
                    ea.variant,
                    ea.user_id,
                    CASE WHEN EXISTS (
                        SELECT 1 FROM transactions t
                        WHERE t.user_id = ea.user_id
                          AND t.type = 'deposit'
                          AND t.status = 'completed'
                    ) THEN 1 ELSE 0 END AS metric_value
                FROM experiment_assignments ea
                WHERE ea.experiment_id = ?
            """
        elif metric == "bet_count":
            query = """
                SELECT
                    ea.variant,
                    ea.user_id,
                    COUNT(b.bet_id) AS metric_value
                FROM experiment_assignments ea
                LEFT JOIN bets b ON b.user_id = ea.user_id
                WHERE ea.experiment_id = ?
                GROUP BY ea.variant, ea.user_id
            """
        elif metric == "ggr":
            query = """
                SELECT
                    ea.variant,
                    ea.user_id,
                    COALESCE(SUM(b.stake - COALESCE(b.actual_payout, 0)), 0) AS metric_value
                FROM experiment_assignments ea
                LEFT JOIN bets b ON b.user_id = ea.user_id
                    AND b.status IN ('won','lost')
                WHERE ea.experiment_id = ?
                GROUP BY ea.variant, ea.user_id
            """
        elif metric == "accumulator_bet_rate":
            query = """
                SELECT
                    ea.variant,
                    ea.user_id,
                    CASE WHEN COUNT(b.bet_id) FILTER (WHERE b.bet_type = 'accumulator') > 0
                         THEN 1 ELSE 0 END AS metric_value
                FROM experiment_assignments ea
                LEFT JOIN bets b ON b.user_id = ea.user_id
                WHERE ea.experiment_id = ?
                GROUP BY ea.variant, ea.user_id
            """
        else:
            raise ValueError(f"Unknown metric: {metric}")
        return self.conn.execute(query, [experiment_id]).df()
