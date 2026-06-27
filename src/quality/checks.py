"""
Data quality checks — run after each ETL load.
Each check returns a QualityResult; the runner raises on any failure.
"""

from dataclasses import dataclass
from typing import Callable
import duckdb
import logging

log = logging.getLogger(__name__)


@dataclass
class QualityResult:
    check:   str
    passed:  bool
    details: str


class DataQualityRunner:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn   = conn
        self._checks: list[Callable[[], QualityResult]] = [
            self._no_null_user_ids,
            self._no_orphan_bets,
            self._no_negative_stakes,
            self._no_future_settled_dates,
            self._stake_vs_payout_consistency,
            self._no_duplicate_bets,
            self._selection_odds_range,
            self._experiment_variant_balance,
        ]

    def run(self, raise_on_failure: bool = True) -> list[QualityResult]:
        results = []
        for check_fn in self._checks:
            result = check_fn()
            status = "PASS" if result.passed else "FAIL"
            log.info("[%s] %s — %s", status, result.check, result.details)
            results.append(result)
        failures = [r for r in results if not r.passed]
        if failures and raise_on_failure:
            names = ", ".join(r.check for r in failures)
            raise RuntimeError(f"Data quality failures: {names}")
        return results

    # ── individual checks ──────────────────────────────────────────────────────

    def _no_null_user_ids(self) -> QualityResult:
        n = self.conn.execute(
            "SELECT COUNT(*) FROM bets WHERE user_id IS NULL"
        ).fetchone()[0]
        return QualityResult(
            check="no_null_user_ids",
            passed=n == 0,
            details=f"{n} bets with NULL user_id",
        )

    def _no_orphan_bets(self) -> QualityResult:
        n = self.conn.execute("""
            SELECT COUNT(*) FROM bets b
            WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.user_id = b.user_id)
        """).fetchone()[0]
        return QualityResult(
            check="no_orphan_bets",
            passed=n == 0,
            details=f"{n} bets reference non-existent users",
        )

    def _no_negative_stakes(self) -> QualityResult:
        n = self.conn.execute(
            "SELECT COUNT(*) FROM bets WHERE stake <= 0"
        ).fetchone()[0]
        return QualityResult(
            check="no_negative_stakes",
            passed=n == 0,
            details=f"{n} bets with stake ≤ 0",
        )

    def _no_future_settled_dates(self) -> QualityResult:
        n = self.conn.execute("""
            SELECT COUNT(*) FROM bets
            WHERE settled_ts IS NOT NULL
              AND settled_ts::TIMESTAMP > NOW()
        """).fetchone()[0]
        return QualityResult(
            check="no_future_settled_dates",
            passed=n == 0,
            details=f"{n} bets with future settled_ts",
        )

    def _stake_vs_payout_consistency(self) -> QualityResult:
        # Won bets must have actual_payout > 0; lost bets must have payout = 0
        n = self.conn.execute("""
            SELECT COUNT(*) FROM bets
            WHERE (status = 'won'  AND (actual_payout IS NULL OR actual_payout <= 0))
               OR (status = 'lost' AND actual_payout IS NOT NULL AND actual_payout > 0)
        """).fetchone()[0]
        return QualityResult(
            check="stake_vs_payout_consistency",
            passed=n == 0,
            details=f"{n} bets with inconsistent payout/status",
        )

    def _no_duplicate_bets(self) -> QualityResult:
        n = self.conn.execute("""
            SELECT COUNT(*) - COUNT(DISTINCT bet_id) FROM bets
        """).fetchone()[0]
        return QualityResult(
            check="no_duplicate_bets",
            passed=n == 0,
            details=f"{n} duplicate bet_id rows",
        )

    def _selection_odds_range(self) -> QualityResult:
        n = self.conn.execute(
            "SELECT COUNT(*) FROM selections WHERE odds < 1.0 OR odds > 1000"
        ).fetchone()[0]
        return QualityResult(
            check="selection_odds_range",
            passed=n == 0,
            details=f"{n} selections with odds outside [1.0, 1000]",
        )

    def _experiment_variant_balance(self) -> QualityResult:
        """Flag experiments where variant split deviates >10 pp from 50/50."""
        df = self.conn.execute("""
            SELECT
                experiment_id,
                SUM(CASE WHEN variant='control'   THEN 1 ELSE 0 END) AS ctrl,
                SUM(CASE WHEN variant='treatment' THEN 1 ELSE 0 END) AS trt,
                COUNT(*) AS total
            FROM experiment_assignments
            GROUP BY experiment_id
        """).df()
        bad = []
        for _, row in df.iterrows():
            if row["total"] > 0:
                split = abs(row["ctrl"] / row["total"] - 0.5)
                if split > 0.10:
                    bad.append(int(row["experiment_id"]))
        return QualityResult(
            check="experiment_variant_balance",
            passed=len(bad) == 0,
            details=f"imbalanced experiments: {bad}" if bad else "all balanced",
        )
