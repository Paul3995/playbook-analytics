"""
Session-scoped DuckDB fixture — generates seed data once per test run.
"""

import pytest
import duckdb
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.seeds.generate_data import (
    gen_users, gen_events, gen_markets_and_selections,
    gen_bets_and_bet_selections, gen_transactions, gen_experiments,
    SPORTS, COMPETITIONS, write_csv,
)
from src.etl.extract import load_csvs_to_duckdb
from src.etl.transform import run_all
from src.etl.load import materialise_marts


@pytest.fixture(scope="session")
def seed_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("seeds")
    users       = gen_users()
    events      = gen_events()
    mkts, sels  = gen_markets_and_selections(events)
    bets, bsels = gen_bets_and_bet_selections(users, sels)
    txns        = gen_transactions(users)
    exps, asgns = gen_experiments()

    def _write(name, rows, fields):
        import csv
        with open(d / f"{name}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    _write("sports",      [{"sport_id": s[0], "name": s[1], "slug": s[2]} for s in SPORTS],
           ["sport_id","name","slug"])
    _write("competitions",[{"competition_id": c[0],"sport_id": c[1],"name": c[2],"country_code": c[3]}
                           for c in COMPETITIONS],
           ["competition_id","sport_id","name","country_code"])
    _write("users",       users,  ["user_id","username","email","country_code","currency","registration_ts","first_deposit_ts","status","vip_tier"])
    _write("events",      events, ["event_id","competition_id","home_team","away_team","scheduled_start","status","result"])
    _write("markets",     mkts,   ["market_id","event_id","market_type","status"])
    _write("selections",  sels,   ["selection_id","market_id","name","odds","result"])
    _write("bets",        bets,   ["bet_id","user_id","bet_type","stake","potential_payout","actual_payout","status","placed_ts","settled_ts","currency"])
    _write("bet_selections", bsels, ["id","bet_id","selection_id","odds_at_place"])
    _write("transactions",   txns,  ["transaction_id","user_id","type","amount","currency","status","created_ts","completed_ts","payment_method"])
    _write("experiments",    exps,  ["experiment_id","name","description","hypothesis","metric","status","start_ts","end_ts","min_sample_size"])
    _write("experiment_assignments", asgns, ["id","experiment_id","user_id","variant","assigned_ts"])
    return str(d)


@pytest.fixture(scope="session")
def conn(seed_dir):
    c = duckdb.connect(":memory:")
    load_csvs_to_duckdb(c, seed_dir)
    run_all(c)
    materialise_marts(c)
    yield c
    c.close()
