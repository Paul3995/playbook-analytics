"""
Synthetic sports betting data generator.
Produces realistic CSV seeds that the ETL pipeline loads into DuckDB.
Run: python -m data.seeds.generate_data
"""

import random
import csv
import os
from datetime import datetime, timedelta

SEED = 42
random.seed(SEED)

OUT_DIR = os.path.join(os.path.dirname(__file__))

# ── configuration ─────────────────────────────────────────────────────────────
N_USERS        = 5_000
N_EVENTS       = 800
N_BETS         = 60_000
START_DATE     = datetime(2024, 1, 1)
END_DATE       = datetime(2024, 6, 30)

SPORTS = [
    (1, "Football",    "football"),
    (2, "Basketball",  "basketball"),
    (3, "Tennis",      "tennis"),
    (4, "Cricket",     "cricket"),
    (5, "Horse Racing","horse_racing"),
]

COMPETITIONS = [
    (1,  1, "English Premier League",  "GB"),
    (2,  1, "Spanish La Liga",         "ES"),
    (3,  1, "UEFA Champions League",   "EU"),
    (4,  1, "Nigerian Premier League", "NG"),
    (5,  2, "NBA",                     "US"),
    (6,  2, "EuroLeague",              "EU"),
    (7,  3, "ATP Tour",                "EU"),
    (8,  3, "WTA Tour",                "EU"),
    (9,  4, "IPL",                     "IN"),
    (10, 5, "UK Horse Racing",         "GB"),
]

MARKET_TYPES = ["1X2", "BTTS", "TOTAL_GOALS", "ASIAN_HANDICAP", "WINNER"]
COUNTRIES    = ["NG", "GB", "GH", "KE", "ZA", "US", "IN", "ES", "DE", "FR"]
CURRENCIES   = ["USD", "GBP", "EUR", "NGN"]
VIP_TIERS    = ["bronze"] * 60 + ["silver"] * 25 + ["gold"] * 12 + ["platinum"] * 3
PAYMENT_METHODS = ["card", "bank_transfer", "crypto", "e_wallet"]


def rand_dt(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def write_csv(filename: str, rows: list[dict], fieldnames: list[str]) -> None:
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {len(rows):>7,} rows → {filename}")


# ── generate tables ────────────────────────────────────────────────────────────

def gen_users() -> list[dict]:
    users = []
    for i in range(1, N_USERS + 1):
        reg_ts = rand_dt(START_DATE, END_DATE - timedelta(days=30))
        users.append({
            "user_id":         i,
            "username":        f"player_{i:05d}",
            "email":           f"player_{i}@example.com",
            "country_code":    random.choice(COUNTRIES),
            "currency":        random.choice(CURRENCIES),
            "registration_ts": reg_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "first_deposit_ts": (reg_ts + timedelta(hours=random.randint(0, 48))).strftime("%Y-%m-%d %H:%M:%S"),
            "status":          random.choices(["active", "suspended", "closed"], weights=[88, 8, 4])[0],
            "vip_tier":        random.choice(VIP_TIERS),
        })
    return users


def gen_events() -> list[dict]:
    events = []
    event_id = 1
    teams = {
        1: ["Man United","Chelsea","Arsenal","Liverpool","City","Tottenham","Newcastle","Rangers",
            "Enyimba","Kano Pillars","Barcelona","Real Madrid","Bayern"],
        2: ["Lakers","Warriors","Celtics","Heat","Bulls","Nets","Suns","Nuggets"],
        3: ["Federer","Djokovic","Nadal","Alcaraz","Sinner","Murray","Medvedev","Rublev"],
        5: ["Red Rum","Speedy Dart","Lucky Star","Iron Duke","Blue Moon","Gold Rush"],
    }
    for _ in range(N_EVENTS):
        comp = random.choice(COMPETITIONS)
        comp_id, sport_id = comp[0], comp[1]
        sport_teams = teams.get(sport_id, ["Team A", "Team B", "Team C"])
        home = random.choice(sport_teams)
        away = random.choice([t for t in sport_teams if t != home] or sport_teams)
        sched = rand_dt(START_DATE, END_DATE)
        status = random.choices(
            ["settled", "live", "prematch", "cancelled"],
            weights=[70, 10, 15, 5]
        )[0]
        result = f"{random.randint(0,4)}-{random.randint(0,4)}" if status == "settled" else None
        events.append({
            "event_id":        event_id,
            "competition_id":  comp_id,
            "home_team":       home,
            "away_team":       away,
            "scheduled_start": sched.strftime("%Y-%m-%d %H:%M:%S"),
            "status":          status,
            "result":          result or "",
        })
        event_id += 1
    return events


def gen_markets_and_selections(events: list[dict]) -> tuple[list, list]:
    markets, selections = [], []
    market_id = sel_id = 1
    for ev in events:
        for mtype in random.sample(MARKET_TYPES, k=random.randint(2, 4)):
            mstatus = "settled" if ev["status"] == "settled" else "open"
            markets.append({
                "market_id":   market_id,
                "event_id":    ev["event_id"],
                "market_type": mtype,
                "status":      mstatus,
            })
            if mtype == "1X2":
                opts = [("Home", 0), ("Draw", 1), ("Away", 2)]
            elif mtype == "BTTS":
                opts = [("Yes", 0), ("No", 1)]
            elif mtype == "TOTAL_GOALS":
                opts = [("Over 2.5", 0), ("Under 2.5", 1)]
            elif mtype == "ASIAN_HANDICAP":
                opts = [("Home -0.5", 0), ("Away +0.5", 1)]
            else:
                opts = [("Home", 0), ("Away", 1)]

            winning_idx = random.randint(0, len(opts) - 1) if mstatus == "settled" else None
            for idx, (name, _) in enumerate(opts):
                odds = round(random.uniform(1.3, 8.0), 2)
                result = None
                if winning_idx is not None:
                    result = "win" if idx == winning_idx else "lose"
                selections.append({
                    "selection_id": sel_id,
                    "market_id":    market_id,
                    "name":         name,
                    "odds":         odds,
                    "result":       result or "",
                })
                sel_id += 1
            market_id += 1
    return markets, selections


def gen_bets_and_bet_selections(
    users: list[dict], selections: list[dict]
) -> tuple[list, list]:
    bets_out, bet_sels_out = [], []
    winning_sel = {s["selection_id"] for s in selections if s["result"] == "win"}
    all_sel_ids = [s["selection_id"] for s in selections]
    sel_odds    = {s["selection_id"]: float(s["odds"]) for s in selections}

    bet_id = bs_id = 1
    for _ in range(N_BETS):
        user = random.choice(users)
        placed_ts = rand_dt(
            datetime.fromisoformat(user["registration_ts"]),
            END_DATE
        )
        bet_type = random.choices(
            ["single", "accumulator", "system"],
            weights=[70, 25, 5]
        )[0]
        n_legs = 1 if bet_type == "single" else random.randint(2, 6)
        chosen = random.sample(all_sel_ids, min(n_legs, len(all_sel_ids)))
        combined_odds = 1.0
        for sid in chosen:
            combined_odds *= sel_odds.get(sid, 2.0)
        combined_odds = round(combined_odds, 3)
        stake = round(random.uniform(1, 500), 2)
        potential = round(stake * combined_odds, 2)

        all_win = all(sid in winning_sel for sid in chosen)
        any_void = random.random() < 0.01
        if any_void:
            status, actual_payout, settled_ts = "void", None, None
        elif all_win:
            status = "won"
            actual_payout = potential
            settled_ts = placed_ts + timedelta(hours=random.randint(1, 72))
        else:
            status = "lost"
            actual_payout = 0.0
            settled_ts = placed_ts + timedelta(hours=random.randint(1, 72))

        # ~10% still pending (recent bets)
        if random.random() < 0.10:
            status, actual_payout, settled_ts = "pending", None, None

        bets_out.append({
            "bet_id":           bet_id,
            "user_id":          user["user_id"],
            "bet_type":         bet_type,
            "stake":            stake,
            "potential_payout": potential,
            "actual_payout":    actual_payout if actual_payout is not None else "",
            "status":           status,
            "placed_ts":        placed_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "settled_ts":       settled_ts.strftime("%Y-%m-%d %H:%M:%S") if settled_ts else "",
            "currency":         user["currency"],
        })
        for sid in chosen:
            bet_sels_out.append({
                "id":            bs_id,
                "bet_id":        bet_id,
                "selection_id":  sid,
                "odds_at_place": sel_odds.get(sid, 2.0),
            })
            bs_id += 1
        bet_id += 1
    return bets_out, bet_sels_out


def gen_transactions(users: list[dict]) -> list[dict]:
    txns = []
    txn_id = 1
    for user in users:
        reg_ts = datetime.fromisoformat(user["registration_ts"])
        n_deposits = random.randint(1, 20)
        for _ in range(n_deposits):
            created_ts = rand_dt(reg_ts, END_DATE)
            completed  = created_ts + timedelta(minutes=random.randint(1, 60))
            txns.append({
                "transaction_id": txn_id,
                "user_id":        user["user_id"],
                "type":           "deposit",
                "amount":         round(random.uniform(10, 2000), 2),
                "currency":       user["currency"],
                "status":         random.choices(["completed","failed","pending"], weights=[90,5,5])[0],
                "created_ts":     created_ts.strftime("%Y-%m-%d %H:%M:%S"),
                "completed_ts":   completed.strftime("%Y-%m-%d %H:%M:%S"),
                "payment_method": random.choice(PAYMENT_METHODS),
            })
            txn_id += 1
        if random.random() < 0.4:
            created_ts = rand_dt(reg_ts, END_DATE)
            txns.append({
                "transaction_id": txn_id,
                "user_id":        user["user_id"],
                "type":           "withdrawal",
                "amount":         round(random.uniform(10, 500), 2),
                "currency":       user["currency"],
                "status":         random.choices(["completed","pending","failed"], weights=[80,15,5])[0],
                "created_ts":     created_ts.strftime("%Y-%m-%d %H:%M:%S"),
                "completed_ts":   (created_ts + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S"),
                "payment_method": random.choice(PAYMENT_METHODS),
            })
            txn_id += 1
    return txns


def gen_experiments() -> tuple[list, list]:
    experiments = [
        {
            "experiment_id": 1,
            "name":          "new_onboarding_flow",
            "description":   "Simplified 3-step deposit flow vs current 5-step",
            "hypothesis":    "Reducing friction in onboarding increases first-deposit rate",
            "metric":        "first_deposit_rate",
            "status":        "completed",
            "start_ts":      "2024-02-01 00:00:00",
            "end_ts":        "2024-02-28 23:59:59",
            "min_sample_size": 500,
        },
        {
            "experiment_id": 2,
            "name":          "odds_boost_promo",
            "description":   "20% odds boost on accumulators for treatment group",
            "hypothesis":    "Odds boost increases accumulator bet frequency",
            "metric":        "accumulator_bet_rate",
            "status":        "running",
            "start_ts":      "2024-05-01 00:00:00",
            "end_ts":        "",
            "min_sample_size": 1000,
        },
        {
            "experiment_id": 3,
            "name":          "cashout_feature_placement",
            "description":   "Prominent vs subtle cashout button placement",
            "hypothesis":    "Prominent cashout button increases cashout utilisation",
            "metric":        "cashout_rate",
            "status":        "completed",
            "start_ts":      "2024-03-15 00:00:00",
            "end_ts":        "2024-04-15 23:59:59",
            "min_sample_size": 800,
        },
    ]
    assignments = []
    a_id = 1
    all_user_ids = list(range(1, N_USERS + 1))
    random.shuffle(all_user_ids)
    for exp in experiments:
        pool = random.sample(all_user_ids, min(exp["min_sample_size"] * 2, len(all_user_ids)))
        for uid in pool:
            variant = "control" if pool.index(uid) % 2 == 0 else "treatment"
            assignments.append({
                "id":             a_id,
                "experiment_id":  exp["experiment_id"],
                "user_id":        uid,
                "variant":        variant,
                "assigned_ts":    exp["start_ts"],
            })
            a_id += 1
    return experiments, assignments


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Generating synthetic betting data...")

    users = gen_users()
    write_csv("users.csv", users, ["user_id","username","email","country_code","currency",
                                   "registration_ts","first_deposit_ts","status","vip_tier"])

    write_csv("sports.csv", [{"sport_id": s[0], "name": s[1], "slug": s[2]} for s in SPORTS],
              ["sport_id","name","slug"])

    write_csv("competitions.csv",
              [{"competition_id": c[0], "sport_id": c[1], "name": c[2], "country_code": c[3]}
               for c in COMPETITIONS],
              ["competition_id","sport_id","name","country_code"])

    events = gen_events()
    write_csv("events.csv", events,
              ["event_id","competition_id","home_team","away_team","scheduled_start","status","result"])

    markets, selections = gen_markets_and_selections(events)
    write_csv("markets.csv",    markets,    ["market_id","event_id","market_type","status"])
    write_csv("selections.csv", selections, ["selection_id","market_id","name","odds","result"])

    bets, bet_sels = gen_bets_and_bet_selections(users, selections)
    write_csv("bets.csv",            bets,     ["bet_id","user_id","bet_type","stake","potential_payout",
                                                 "actual_payout","status","placed_ts","settled_ts","currency"])
    write_csv("bet_selections.csv",  bet_sels, ["id","bet_id","selection_id","odds_at_place"])

    txns = gen_transactions(users)
    write_csv("transactions.csv", txns, ["transaction_id","user_id","type","amount","currency",
                                          "status","created_ts","completed_ts","payment_method"])

    experiments, assignments = gen_experiments()
    write_csv("experiments.csv", experiments,
              ["experiment_id","name","description","hypothesis","metric","status",
               "start_ts","end_ts","min_sample_size"])
    write_csv("experiment_assignments.csv", assignments,
              ["id","experiment_id","user_id","variant","assigned_ts"])

    print(f"\nDone. Files written to: {OUT_DIR}")


if __name__ == "__main__":
    main()
