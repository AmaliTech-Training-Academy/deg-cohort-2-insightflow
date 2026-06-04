# metabase_setup.py

import logging

import psycopg2
from config import METABASE_URL, PG_CONFIG  # type: ignore[attr-defined]
from customer.cards import TAB4_CARDS
from customer.views import VIEWS_SQL as CUSTOMER_VIEWS
from metabase_client import (
    build_tabbed_dashboard,
    clean_up,
    create_filter_value_cards,
    get_existing_dashboard_id,
    get_or_create_database,
    login,
    set_homepage,
    setup_metabase,
    wait_for_metabase,
)

# Import cards for each tab
from overview.cards import TAB0_CARDS
from products.cards import TAB2_CARDS
from products.views import VIEWS_SQL as PRODUCTS_VIEWS
from regional.cards import TAB3_CARDS
from regional.views import VIEWS_SQL as REGIONAL_VIEWS
from sales.cards import TAB1_CARDS

# Import SQL views for each tab
from sales.views import VIEWS_SQL as SALES_VIEWS

# ----------------------------
# Logging configuration
# ----------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("InsightFlowDashboard")


# ----------------------------
# Helper: create SQL views
# ----------------------------
def create_views(*views_list):
    """Drop and recreate all SQL views in PostgreSQL for the dashboard."""
    logger.info("Creating SQL views...")
    with psycopg2.connect(**PG_CONFIG) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            for views_sql in views_list:
                for statement in views_sql.strip().split(";"):
                    statement = statement.strip()
                    if statement:
                        try:
                            view_name = next(
                                (w for w in statement.split() if w.startswith("v_")),
                                "?",
                            )
                            cur.execute(f"DROP VIEW IF EXISTS {view_name} CASCADE;")
                            cur.execute(statement + ";")
                            logger.info(f"[OK] Created view: {view_name}")
                        except Exception as e:
                            logger.warning(
                                f"[WARN] Failed to create view {view_name}: {e}"
                            )


# ----------------------------
# Main orchestration
# ----------------------------
def main():
    logger.info("Starting InsightFlow Analytics full dashboard setup...")

    # Wait for Metabase to be ready
    wait_for_metabase()

    # Run first-time setup if this is a fresh install
    setup_metabase()

    # Login to Metabase
    session_id = login()

    # Create SQL views for all tabs
    create_views(SALES_VIEWS, PRODUCTS_VIEWS, REGIONAL_VIEWS, CUSTOMER_VIEWS)

    # Connect or create the warehouse database
    database_id = get_or_create_database(session_id)

    # Check if the dashboard already exists — skip full rebuild if so
    dashboard_id = get_existing_dashboard_id(session_id)
    if dashboard_id:
        logger.info(
            "Dashboard already exists (ID: %s). Skipping rebuild.", dashboard_id
        )
        logger.info("Access it at: %s/dashboard/%s", METABASE_URL, dashboard_id)
        return

    # First-time build: clean up any stale cards, then create everything fresh
    clean_up(session_id)

    # Create filter value cards
    create_filter_value_cards(session_id, database_id)

    # Dashboard parameters (filters)
    all_params = [
        {"id": "p_date_range", "type": "date/range", "name": "Date Range"},
        {"id": "p_category", "type": "string/=", "name": "Category"},
        {"id": "p_country", "type": "string/=", "name": "Country"},
        {"id": "p_region", "type": "string/=", "name": "Region"},
    ]

    # Build single dashboard with 5 tabs
    tabs = [
        ("Overview", TAB0_CARDS),
        ("Sales & Revenue", TAB1_CARDS),
        ("Products & Inventory", TAB2_CARDS),
        ("Regional Analysis", TAB3_CARDS),
        ("Customer Intelligence", TAB4_CARDS),
    ]
    dashboard_id = build_tabbed_dashboard(
        session_id, database_id, tabs, parameters=all_params
    )

    # Set as homepage so users land on the dashboard after login
    set_homepage(session_id, dashboard_id)

    logger.info("InsightFlow Analytics dashboard created successfully!")
    logger.info("Access it at: %s/dashboard/%s", METABASE_URL, dashboard_id)


# ----------------------------
# Entry point
# ----------------------------
if __name__ == "__main__":
    main()
