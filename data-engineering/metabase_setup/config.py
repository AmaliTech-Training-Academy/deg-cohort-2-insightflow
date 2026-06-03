# config.py
# Loads environment variables from .env and exposes typed config constants.

import os
from pathlib import Path
from typing import Optional


def load_dotenv(env_path: Optional[Path] = None) -> None:
    """Load key=value pairs from a .env file into os.environ (no overwrites).
    Supports ${VAR} expansion inside values. Defaults to <project-root>/.env.
    """
    if env_path is None:
        env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        value = os.path.expandvars(value)  # expand ${VAR} references
        if key and key not in os.environ:
            os.environ[key] = value


load_dotenv()


def required_env(name: str) -> str:
    """Return the value of a required environment variable, or raise EnvironmentError."""
    value = os.getenv(name)
    if value is None:
        raise EnvironmentError(
            f"Required environment variable {name} is not set.\n"
            "Add it to your environment or to a .env file based on .env.example"
        )
    return value


METABASE_URL = os.getenv("METABASE_URL", "http://localhost:3002")
MB_ADMIN_EMAIL = os.getenv("METABASE_ADMIN_EMAIL")
MB_ADMIN_PASSWORD = required_env("METABASE_ADMIN_PASSWORD")

PG_CONFIG = {
    "host": os.getenv("WAREHOUSE_DB_HOST"),
    "port": int(os.getenv("WAREHOUSE_DB_PORT", 5432)),
    "dbname": os.getenv("WAREHOUSE_DB_NAME"),
    "user": os.getenv("WAREHOUSE_DB_USER"),
    "password": required_env("WAREHOUSE_DB_PASSWORD"),
}

METABASE_DB_CONFIG = {
    "engine": "postgres",
    "name": os.getenv("METABASE_DB_NAME", "InsightFlow Warehouse"),
    "details": {
        "host": os.getenv("METABASE_DB_HOST"),
        "port": int(os.getenv("METABASE_DB_PORT", 5432)),
        "dbname": os.getenv("METABASE_DB_DATABASE"),
        "user": os.getenv("METABASE_DB_USER"),
        "password": os.getenv("METABASE_DB_PASSWORD"),
        "ssl": False,
    },
}
