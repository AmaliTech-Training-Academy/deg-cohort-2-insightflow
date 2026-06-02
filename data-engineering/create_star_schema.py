"""Create the InsightFlow star-schema on the target warehouse database.

Reads DDL from warehouse/schema.sql and executes every statement against
the warehouse connection configured via environment variables.  Safe to run
multiple times (all statements use IF NOT EXISTS).

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

SCHEMA_FILE = Path(__file__).parent / "warehouse" / "schema.sql"


def _parse_sql(sql: str) -> list[str]:
    """Split a SQL file into individual executable statements.

    Strips single-line (--) and block (/* */) comments before splitting on
    statement-terminating semicolons so comment content cannot fool the
    splitter.
    """
    # Remove block comments
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    # Remove single-line comments (but keep newlines to preserve line counts)
    sql = re.sub(r"--[^\n]*", "", sql)
    statements = [s.strip() for s in sql.split(";")]
    return [s for s in statements if s]


def create_schema(database_url: str = DATABASE_URL) -> None:
    """Create all star-schema tables and indexes in the warehouse database."""
    log.info("Connecting to warehouse: %s", database_url.split("@")[-1])

    raw_sql = SCHEMA_FILE.read_text(encoding="utf-8")
    statements = _parse_sql(raw_sql)

    engine = create_engine(database_url, echo=False)
    created = 0

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
            first_line = stmt.splitlines()[0][:80]
            log.info("  ✓  %s …", first_line)
            created += 1

    log.info("Star schema ready — %d statements executed.", created)
    engine.dispose()


if __name__ == "__main__":
    create_schema()
