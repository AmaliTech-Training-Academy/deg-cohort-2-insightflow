# metabase_setup.py
import logging

import psycopg2

from config import METABASE_URL, PG_CONFIG
from metabase_client import (
    build_dashboard,
    clean_up,
    get_or_create_database,
    login,
    wait_for_metabase,
)
from sales_dashboard_cards import CARDS
from sales_dashboard_views import VIEWS_SQL

logging.basicConfig(
    level="INFO",
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger("insightflow")

def create_views() -> None:
    """Drop and recreate all analytics views in PostgreSQL."""
    log.info("Creating views...")
    with psycopg2.connect(**PG_CONFIG) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            for view in ("v_weekly_summary", "v_monthly_revenue", "v_daily_revenue", "v_kpi_summary"):
                cur.execute(f"DROP VIEW IF EXISTS {view} CASCADE;")
            for statement in VIEWS_SQL.strip().split(";"):
                statement = statement.strip()
                if statement:
                    cur.execute(statement + ";")
                    view_name = next((w for w in statement.split() if w.startswith("v_")), "?")
                    log.info("  [OK] %s", view_name)


def main() -> None:
    """Run the full setup sequence end-to-end."""
    wait_for_metabase()
    session_id = login()
    create_views()
    database_id = get_or_create_database(session_id)
    clean_up(session_id)
    dashboard_id = build_dashboard(session_id, database_id, CARDS)
    log.info("Done → %s/dashboard/%s", METABASE_URL, dashboard_id)


if __name__ == "__main__":
    main()
