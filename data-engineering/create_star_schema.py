"""Create the InsightFlow star-schema on the target warehouse database.

Reads DDL from warehouse/schema.sql and executes every statement against
the warehouse connection configured via environment variables.  Safe to run
multiple times (all statements use IF NOT EXISTS).

Designed to run as a Docker init container:
  - Retries the DB connection up to MAX_RETRIES times with RETRY_DELAY
    seconds between attempts so it survives a slow container start-up.
  - Exits 0 on success, 1 on unrecoverable failure.
"""

import logging
import re
import sys
import time
from pathlib import Path

from config import WAREHOUSE_DATABASE_URL
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

SCHEMA_FILE = Path(__file__).parent / "warehouse" / "schema.sql"
MAX_RETRIES = 10
RETRY_DELAY = 5  # seconds between connection attempts


def _parse_sql(sql: str) -> list[str]:
    """Strip comments and split on semicolons into executable statements."""
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", "", sql)
    return [s.strip() for s in sql.split(";") if s.strip()]


def create_schema(database_url: str = WAREHOUSE_DATABASE_URL) -> None:
    """Create all star-schema tables and indexes in the warehouse database.

    Retries the initial connection up to MAX_RETRIES times so this function
    can be called immediately after the DB container starts.

    Raises
    ------
    SystemExit(1)
        On unrecoverable error after all retries are exhausted.
    """
    log.info("Target warehouse: %s", database_url.split("@")[-1])

    raw_sql = SCHEMA_FILE.read_text(encoding="utf-8")
    statements = _parse_sql(raw_sql)
    log.info("Parsed %d DDL statements from schema.sql", len(statements))

    engine = create_engine(database_url, echo=False)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with engine.begin() as conn:
                for stmt in statements:
                    conn.execute(text(stmt))
                    log.info("  OK  %s", stmt.splitlines()[0][:80])
            log.info("Star schema ready — %d statements executed.", len(statements))
            engine.dispose()
            return
        except OperationalError as exc:
            if attempt < MAX_RETRIES:
                log.warning(
                    "DB not reachable (attempt %d/%d) — retrying in %ds: %s",
                    attempt,
                    MAX_RETRIES,
                    RETRY_DELAY,
                    exc.orig,
                )
                time.sleep(RETRY_DELAY)
            else:
                log.error(
                    "Cannot reach warehouse DB after %d attempts — aborting.",
                    MAX_RETRIES,
                )
                engine.dispose()
                sys.exit(1)
        except SQLAlchemyError as exc:
            log.error("Schema creation failed: %s", exc)
            engine.dispose()
            sys.exit(1)
if __name__ == "__main__":
    create_schema()
