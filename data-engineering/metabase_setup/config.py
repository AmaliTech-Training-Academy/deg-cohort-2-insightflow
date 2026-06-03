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
        value = os.path.expandvars(value)
        if key and key not in os.environ:
            os.environ[key] = value


def _env(*names, default=None):
    """Return the first set env var from the given names, or default."""
    for name in names:
        v = os.getenv(name)
        if v is not None:
            return v
    return default


def _required_env(*names):
    """Return the first set env var from the given names, or raise."""
    v = _env(*names)
    if v is None:
        raise EnvironmentError(
            f"One of {names} must be set in your environment or .env file."
        )
    return v


load_dotenv()

# Metabase connection
METABASE_URL = os.getenv("METABASE_URL", "http://localhost:3001")
MB_ADMIN_EMAIL = os.getenv("METABASE_ADMIN_EMAIL")
MB_ADMIN_PASSWORD = _required_env("METABASE_ADMIN_PASSWORD")

# psycopg2 connection used by the setup script to create SQL views
PG_CONFIG = {
    "host": _env("PG_HOST", "WAREHOUSE_DB_HOST"),
    "port": int(_env("PG_PORT", "WAREHOUSE_DB_PORT", default="5432")),
    "dbname": _env("PG_DATABASE", "WAREHOUSE_DB_NAME"),
    "user": _env("PG_USER", "WAREHOUSE_DB_USER"),
    "password": _required_env("PG_PASSWORD", "WAREHOUSE_DB_PASSWORD"),
}

# Metabase data-source registration
# Falls back to WAREHOUSE_DB_* variables if METABASE_DB_* are not set.
METABASE_DB_CONFIG = {
    "engine": "postgres",
    "name": _env("METABASE_DB_NAME", default="InsightFlow Warehouse"),
    "details": {
        "host": _env("METABASE_DB_HOST", "WAREHOUSE_DB_HOST"),
        "port": int(_env("METABASE_DB_PORT", "WAREHOUSE_DB_PORT", default="5432")),
        "dbname": _env("METABASE_DB_DATABASE", "WAREHOUSE_DB_NAME"),
        "user": _env("METABASE_DB_USER", "WAREHOUSE_DB_USER"),
        "password": _env("METABASE_DB_PASSWORD", "WAREHOUSE_DB_PASSWORD"),
        "ssl": False,
    },
}
