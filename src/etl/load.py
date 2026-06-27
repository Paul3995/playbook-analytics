"""
Load layer — materialises key analytical tables from views.
Materalised tables speed up repeated dashboard queries.
"""

import duckdb
import logging

log = logging.getLogger(__name__)

MATERIALISED = {
    "mart_daily_ggr":          "SELECT * FROM v_daily_ggr",
    "mart_player_rfm":         "SELECT * FROM v_rfm",
    "mart_acquisition_funnel": "SELECT * FROM v_acquisition_funnel",
}


def materialise_marts(conn: duckdb.DuckDBPyConnection) -> None:
    for table, query in MATERIALISED.items():
        conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.execute(f"CREATE TABLE {table} AS {query}")
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        log.info("materialised %-30s  %8d rows", table, n)
