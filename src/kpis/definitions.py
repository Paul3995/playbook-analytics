"""
KPI catalogue — single source of truth for metric definitions.
Each KPI is a dataclass that describes what it measures, its target,
and the SQL / Python function used to compute it.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KPI:
    name:        str
    display:     str
    description: str
    unit:        str                  # 'currency', 'count', 'pct', 'ratio'
    target:      Optional[float]      # business target value
    tags:        list[str] = field(default_factory=list)


REGISTRY: dict[str, KPI] = {
    "ggr_daily": KPI(
        name="ggr_daily",
        display="Daily GGR",
        description="Gross Gaming Revenue: total stakes minus total payouts for settled bets",
        unit="currency",
        target=None,
        tags=["revenue", "core"],
    ),
    "hold_pct": KPI(
        name="hold_pct",
        display="Hold %",
        description="GGR as a percentage of total stakes — platform margin",
        unit="pct",
        target=6.0,
        tags=["revenue", "core"],
    ),
    "dap": KPI(
        name="dap",
        display="Daily Active Players",
        description="Unique players who placed at least one bet on a given day",
        unit="count",
        target=None,
        tags=["engagement"],
    ),
    "map": KPI(
        name="map",
        display="Monthly Active Players",
        description="Unique players who placed at least one bet in a calendar month",
        unit="count",
        target=None,
        tags=["engagement"],
    ),
    "arpu": KPI(
        name="arpu",
        display="ARPU",
        description="Average Revenue Per (active) User in a given month",
        unit="currency",
        target=None,
        tags=["revenue", "engagement"],
    ),
    "day1_retention": KPI(
        name="day1_retention",
        display="Day-1 Retention",
        description="% of new bettors who return to place a bet on the following day",
        unit="pct",
        target=30.0,
        tags=["retention"],
    ),
    "day7_retention": KPI(
        name="day7_retention",
        display="Day-7 Retention",
        description="% of new bettors active 7 days after first bet",
        unit="pct",
        target=20.0,
        tags=["retention"],
    ),
    "day30_retention": KPI(
        name="day30_retention",
        display="Day-30 Retention",
        description="% of new bettors active 30 days after first bet",
        unit="pct",
        target=12.0,
        tags=["retention"],
    ),
    "ftd_rate": KPI(
        name="ftd_rate",
        display="First Time Deposit Rate",
        description="% of registrations that complete a first deposit",
        unit="pct",
        target=40.0,
        tags=["acquisition"],
    ),
    "first_bet_rate": KPI(
        name="first_bet_rate",
        display="First Bet Rate",
        description="% of first depositors who place at least one bet",
        unit="pct",
        target=75.0,
        tags=["acquisition"],
    ),
}
