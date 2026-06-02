import os

from dotenv import load_dotenv

load_dotenv()

# ── Source: OLTP application database on AWS RDS ──────────────────────────────
SOURCE_DB_CONFIG = {
    "host":     os.getenv("RDS_SOURCE_HOST",     "PLACEHOLDER_RDS_ENDPOINT"),
    "port":     os.getenv("RDS_SOURCE_PORT",     "5432"),
    "database": os.getenv("RDS_SOURCE_DB_NAME",  "insightflow_app"),
    "user":     os.getenv("RDS_SOURCE_USER",     "PLACEHOLDER_USER"),
    "password": os.getenv("RDS_SOURCE_PASSWORD", "PLACEHOLDER_PASSWORD"),
}

SOURCE_DATABASE_URL = (
    f"postgresql://{SOURCE_DB_CONFIG['user']}:{SOURCE_DB_CONFIG['password']}"
    f"@{SOURCE_DB_CONFIG['host']}:{SOURCE_DB_CONFIG['port']}/{SOURCE_DB_CONFIG['database']}"
)

# ── Target: OLAP star-schema warehouse on AWS RDS ─────────────────────────────
WAREHOUSE_DB_CONFIG = {
    "host":     os.getenv("RDS_WAREHOUSE_HOST",     "PLACEHOLDER_RDS_ENDPOINT"),
    "port":     os.getenv("RDS_WAREHOUSE_PORT",     "5432"),
    "database": os.getenv("RDS_WAREHOUSE_DB_NAME",  "insightflow_star_schema"),
    "user":     os.getenv("RDS_WAREHOUSE_USER",     "PLACEHOLDER_USER"),
    "password": os.getenv("RDS_WAREHOUSE_PASSWORD", "PLACEHOLDER_PASSWORD"),
}

WAREHOUSE_DATABASE_URL = (
    f"postgresql://{WAREHOUSE_DB_CONFIG['user']}:{WAREHOUSE_DB_CONFIG['password']}"
    f"@{WAREHOUSE_DB_CONFIG['host']}:{WAREHOUSE_DB_CONFIG['port']}/{WAREHOUSE_DB_CONFIG['database']}"
)

# Legacy alias — keeps etl_pipeline.py working without changes
DATABASE_URL = WAREHOUSE_DATABASE_URL
