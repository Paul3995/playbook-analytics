# Playbook Analytics

A production-style sports betting analytics platform built to demonstrate end-to-end data analyst skills: SQL, Python ETL, KPI monitoring, A/B testing, Airflow orchestration, and data quality validation.

---

## Stack

| Layer | Technology |
|---|---|
| Analytical DB | DuckDB (MySQL-compatible SQL; swappable for Redshift) |
| ETL | Python 3.11 |
| Orchestration | Apache Airflow 2.8 |
| Statistical testing | SciPy (z-test, Welch's t-test, Mann-Whitney U) |
| Testing | pytest |
| CI | GitHub Actions |

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     Airflow Orchestration                      │
│                                                                │
│  daily_kpi_pipeline (06:00 UTC)                                │
│  ┌──────────┐  ┌─────────┐  ┌───────────┐  ┌──────┐  ┌─────┐ │
│  │ Extract  │→ │ Quality │→ │ Transform │→ │ Load │→ │ KPI │ │
│  │ CSV→Duck │  │  Checks │  │   Views   │  │ Mart │  │Score│ │
│  └──────────┘  └─────────┘  └───────────┘  └──────┘  └─────┘ │
│                                                                │
│  ab_test_monitor (every 6h)      weekly_report (Mon 08:00)    │
│  ┌──────────────────────────┐    ┌──────────────────────────┐  │
│  │ z-test / t-test per      │    │ GGR · Retention · ARPU   │  │
│  │ running experiment       │    │ RFM Segments             │  │
│  └──────────────────────────┘    └──────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘

Data Model (MySQL schema → DuckDB in dev)
  users → bets → bet_selections → selections → markets → events
       ↘ transactions
       ↘ experiment_assignments → experiments
```

---

## Project Structure

```
playbook-analytics/
│
├── .github/workflows/ci.yml          # GitHub Actions (Python 3.11 & 3.12)
│
├── dags/
│   ├── daily_kpi_pipeline.py         # Extract → QC → Transform → Load → Scorecard
│   ├── ab_test_monitor_dag.py        # Significance check every 6 h
│   └── weekly_report_dag.py          # GGR, retention, ARPU, RFM report
│
├── src/
│   ├── etl/
│   │   ├── extract.py                # Load CSVs → DuckDB
│   │   ├── transform.py              # Analytical views (GGR, RFM, funnel)
│   │   └── load.py                   # Materialise mart tables
│   ├── kpis/
│   │   ├── definitions.py            # KPI catalogue (name, description, target)
│   │   └── calculator.py             # GGR, DAP, retention cohorts, ARPU, scorecard
│   ├── ab_testing/
│   │   ├── experiment.py             # Variant assignment, sample size calc
│   │   └── analysis.py              # z-test, Welch t-test, Mann-Whitney, CI
│   └── quality/
│       └── checks.py                 # 8 data quality checks
│
├── sql/
│   ├── schema/betting_schema.sql     # Full MySQL schema
│   ├── kpis/
│   │   ├── ggr_daily.sql             # GGR + hold %
│   │   ├── active_players.sql        # DAP / WAP / MAP
│   │   ├── player_retention.sql      # Cohort retention + churn
│   │   ├── arpu_ltv.sql              # ARPU & player LTV
│   │   └── bet_volume.sql            # Stakes, margins by sport/market
│   └── analytics/
│       ├── sport_performance.sql     # GGR by sport, live vs prematch split
│       ├── player_segments.sql       # RFM segmentation
│       └── market_margins.sql        # Actual vs theoretical hold, odds calibration
│
├── data/seeds/generate_data.py       # Synthetic data generator (5k users, 60k bets)
│
├── tests/
│   ├── conftest.py                   # Session-scoped DuckDB fixture
│   ├── test_kpis.py                  # KPI calculator tests
│   ├── test_ab_testing.py            # Statistical analysis + experiment manager tests
│   ├── test_quality.py               # Data quality check tests
│   └── test_transforms.py            # ETL view tests
│
├── config/settings.py                # Central config; reads .env
├── .env.example
├── requirements.txt
└── README.md
```

---

## Key KPIs Tracked

| KPI | Definition | Target |
|---|---|---|
| GGR | Stakes − Payouts (settled bets) | — |
| Hold % | GGR / Stakes × 100 | 6% |
| DAP / WAP / MAP | Unique bettors per day/week/month | — |
| ARPU | Monthly GGR ÷ Active Players | — |
| Day-1 Retention | % who bet again next day | 30% |
| Day-7 Retention | % active 7 days after first bet | 20% |
| Day-30 Retention | % active 30 days after first bet | 12% |
| FTD Rate | % registrations completing first deposit | 40% |
| Player LTV | Cumulative GGR per player | — |

---

## How to Run Locally

### Prerequisites
- Python 3.11+

### 1. Clone & install

```bash
git clone https://github.com/Paul3995/playbook-analytics.git
cd playbook-analytics
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Generate seed data

```bash
python -m data.seeds.generate_data
# Writes 11 CSV files to data/seeds/
```

### 3. Run the full ETL pipeline

```python
import duckdb
from src.etl.extract   import load_csvs_to_duckdb
from src.etl.transform import run_all
from src.etl.load      import materialise_marts

conn = duckdb.connect("playbook.duckdb")
load_csvs_to_duckdb(conn, "data/seeds")
run_all(conn)
materialise_marts(conn)
```

### 4. Query KPIs

```python
from datetime import date
from src.kpis.calculator import KPICalculator

calc = KPICalculator(conn)

# Daily GGR + hold %
print(calc.daily_ggr(date(2024,1,1), date(2024,6,30)))

# 30-day KPI scorecard
print(calc.scorecard(date(2024,6,30)))

# Retention cohorts
print(calc.retention_cohorts(date(2024,1,1), date(2024,3,31)))
```

### 5. Run A/B test analysis

```python
from src.ab_testing.experiment import ExperimentManager
from src.ab_testing.analysis   import analyse, summary_table

mgr    = ExperimentManager(conn)
data   = mgr.get_metric_data(1, "first_deposit_rate")
result = analyse(data, "new_onboarding_flow", "first_deposit_rate")

print(f"Lift: {result.relative_lift:.1f}%  p={result.p_value:.4f}  significant={result.is_significant}")
```

### 6. Run the test suite

```bash
pytest tests/ -v --tb=short
```

---

## A/B Testing Framework

Supports three statistical tests — automatically selected based on the metric:

| Metric type | Test |
|---|---|
| Conversion rate (binary) | Two-proportion z-test |
| Continuous (revenue, bet count) | Welch's t-test |
| Non-parametric fallback | Mann-Whitney U |

Sample size is estimated with the Fleiss approximation before experiments launch:

```python
from src.ab_testing.experiment import ExperimentConfig, required_sample_size

cfg = ExperimentConfig(
    name="odds_boost_promo",
    metric="accumulator_bet_rate",
    baseline_rate=0.25,
    min_detectable=0.10,   # 10% relative lift
    alpha=0.05,
    power=0.80,
)
print(required_sample_size(cfg))   # → 1 234 per variant
```

---

## Data Quality Checks

Eight automated checks run after every extract:

| Check | What it validates |
|---|---|
| no_null_user_ids | No bets reference a NULL user |
| no_orphan_bets | Every bet has a matching user record |
| no_negative_stakes | All stakes are > 0 |
| no_future_settled_dates | No settled_ts in the future |
| stake_vs_payout_consistency | Won bets have payout > 0; lost bets have payout = 0 |
| no_duplicate_bets | bet_id is unique |
| selection_odds_range | All odds are within [1.0, 1000] |
| experiment_variant_balance | No experiment split deviates >10 pp from 50/50 |

---

## Sample Output

**KPI Scorecard (trailing 30 days)**

```
        kpi       value      unit   target
    GGR (30d)  412 839.22  currency    None
      Hold %        6.11       pct     6.0
    Avg DAP      1 243.0     count    None
```

**A/B Test Summary**

```
Experiment               Metric              Test                 Control n  Treatment n  Control mean  Treatment mean  Lift %  p-value  Significant
new_onboarding_flow  first_deposit_rate  two-proportion z-test    500          500          0.3820        0.4460        16.75   0.0034      YES
odds_boost_promo     accumulator_bet_rate two-proportion z-test   480          482          0.2460        0.2690         9.35   0.2141       no
```

**RFM Segments**

```
     Segment   players   avg_spend
   Champions      123    4 512.33
Loyal Players      841    1 234.11
Potential Loyalists 1 023   612.44
    New Players    890    189.22
   Occasional    1 234    98.44
     At Risk      412    67.11
     Churned      477     0.00
```
