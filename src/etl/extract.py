"""
Extract layer — loads CSV seed files into DuckDB as tables.
In a production environment this layer would read from MySQL / Redshift
using the same interface (just swap the read_ call).
"""

import duckdb
import os
import logging

log = logging.getLogger(__name__)

TABLES = [
    "sports",
    "competitions",
    "users",
    "events",
    "markets",
    "selections",
    "bets",
    "bet_selections",
    "transactions",
    "experiments",
    "experiment_assignments",
]


def load_csvs_to_duckdb(conn: duckdb.DuckDBPyConnection, seed_dir: str) -> None:
    for table in TABLES:
        path = os.path.join(seed_dir, f"{table}.csv")
        if not os.path.exists(path):
            log.warning("seed file not found, skipping: %s", path)
            continue
        conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.execute(f"""
            CREATE TABLE {table} AS
            SELECT * FROM read_csv_auto('{path}', header=True, nullstr='')
        """)
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        log.info("loaded %-25s  %8d rows", table, n)
