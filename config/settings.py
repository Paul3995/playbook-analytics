import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", 3306))
DB_NAME     = os.getenv("DB_NAME", "sporty")
DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "playbook.duckdb")

DATA_RAW_DIR       = os.getenv("DATA_RAW_DIR", "data/raw")
DATA_PROCESSED_DIR = os.getenv("DATA_PROCESSED_DIR", "data/processed")

# Statistical significance threshold for A/B tests
AB_ALPHA = float(os.getenv("AB_ALPHA", 0.05))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
