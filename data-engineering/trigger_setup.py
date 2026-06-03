"""Install or remove ETL notification triggers on the OLTP source database.

Usage
-----
    python trigger_setup.py install   # install triggers (default)
    python trigger_setup.py remove    # remove triggers and trigger function
    python trigger_setup.py status    # show which triggers are installed

The install command is idempotent — safe to run multiple times.
Triggers are installed on the OLTP source database (insightflow_app), not the
warehouse.  All connection details are read from environment variables via .env.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

import os  # noqa: E402  (after dotenv so env vars are available)

log = logging.getLogger("insightflow.trigger_setup")

_TRIGGERS_SQL = Path(__file__).parent / "etl" / "triggers.sql"

_REMOVE_SQL = """
DROP TRIGGER IF EXISTS trg_etl_pos       ON "posTransactionLine";
DROP TRIGGER IF EXISTS trg_etl_online    ON "onlineOrderLine";
DROP TRIGGER IF EXISTS trg_etl_feedback  ON "feedbackSurvey";
DROP TRIGGER IF EXISTS trg_etl_inventory ON "inventory";
DROP FUNCTION IF EXISTS notify_etl_trigger();
"""

_STATUS_SQL = """
SELECT
    trigger_name,
    event_object_table  AS table_name,
    event_manipulation  AS event,
    action_timing       AS timing
FROM information_schema.triggers
WHERE trigger_name LIKE 'trg_etl_%'
ORDER BY table_name;
"""

_SOURCE_DSN = (
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'insightflow_app')} "
    f"user={os.getenv('DB_USER', 'postgres')} "
    f"password={os.getenv('DB_PASSWORD', 'postgres')}"
)


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(_SOURCE_DSN)


def install() -> None:
    """Install NOTIFY triggers on the OLTP source database."""
    sql = _TRIGGERS_SQL.read_text(encoding="utf-8")
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    log.info("ETL notification triggers installed on '%s'", os.getenv("DB_NAME"))
    print("ETL triggers installed successfully.")


def remove() -> None:
    """Remove NOTIFY triggers and the shared trigger function."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(_REMOVE_SQL)
        conn.commit()
    log.info("ETL notification triggers removed.")
    print("ETL triggers removed.")


def status() -> None:
    """Print which ETL triggers are currently installed."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(_STATUS_SQL)
            rows = cur.fetchall()

    if not rows:
        print("No ETL triggers installed.")
        return

    print(f"\n{'Trigger':<30} {'Table':<25} {'Event':<10} {'Timing'}")
    print("-" * 80)
    for trigger_name, table_name, event, timing in rows:
        print(f"  {trigger_name:<28} {table_name:<23} {event:<10} {timing}")
    print()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    cmd = sys.argv[1] if len(sys.argv) > 1 else "install"
    if cmd == "install":
        install()
    elif cmd == "remove":
        remove()
    elif cmd == "status":
        status()
    else:
        print(f"Unknown command '{cmd}'. Use: install | remove | status")
        sys.exit(1)
