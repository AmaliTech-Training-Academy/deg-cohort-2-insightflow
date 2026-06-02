import os

from dotenv import load_dotenv

load_dotenv()

# ── Source: OLTP application database on AWS RDS ──────────────────────────────
SOURCE_DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "insightflow_app"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

SOURCE_DATABASE_URL = (
    f"postgresql://{SOURCE_DB_CONFIG['user']}:"
    f"{SOURCE_DB_CONFIG['password']}@"
    f"{SOURCE_DB_CONFIG['host']}:{SOURCE_DB_CONFIG['port']}/"
    f"{SOURCE_DB_CONFIG['database']}"
)

# ── Target: OLAP star-schema warehouse on AWS RDS ─────────────────────────────
WAREHOUSE_DB_CONFIG = {
    "host": os.getenv("WAREHOUSE_DB_HOST", "localhost"),
    "port": os.getenv("WAREHOUSE_DB_PORT", "5432"),
    "database": os.getenv("WAREHOUSE_DB_NAME", "insightflow_warehouse"),
    "user": os.getenv("WAREHOUSE_DB_USER", "postgres"),
    "password": os.getenv("WAREHOUSE_DB_PASSWORD", "postgres"),
}

WAREHOUSE_DATABASE_URL = (
    f"postgresql://{WAREHOUSE_DB_CONFIG['user']}:"
    f"{WAREHOUSE_DB_CONFIG['password']}@"
    f"{WAREHOUSE_DB_CONFIG['host']}:{WAREHOUSE_DB_CONFIG['port']}/"
    f"{WAREHOUSE_DB_CONFIG['database']}"
)

# Legacy alias — keeps etl_pipeline.py working without changes
DATABASE_URL = WAREHOUSE_DATABASE_URL
