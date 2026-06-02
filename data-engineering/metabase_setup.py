"""InsightFlow Metabase setup — builds the InsightFlow Analytics dashboard automatically."""

import os
import re
import time
import logging
from pathlib import Path

import psycopg2
import requests

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger("insightflow")


# ── Environment ───────────────────────────────────────────────────────────────

def load_dotenv(env_path: Path) -> None:
    """Load key=value pairs from a .env file into os.environ (no overwrites)."""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


# ── Configuration (all values from .env) ──────────────────────────────────────

METABASE_URL      = os.getenv("METABASE_URL",          "http://localhost:3002")
METABASE_EMAIL    = os.getenv("METABASE_ADMIN_EMAIL",   "admin@insightflow.local")
METABASE_PASSWORD = os.environ["METABASE_ADMIN_PASSWORD"]

DASHBOARD_NAME = "InsightFlow Analytics"

# Direct Postgres connection — used to create views
POSTGRES_CONFIG = {
    "host":     os.getenv("PG_HOST",     "localhost"),
    "port":     int(os.getenv("PG_PORT", "5437")),
    "dbname":   os.getenv("PG_DATABASE", "insightflow_warehouse"),
    "user":     os.getenv("PG_USER",     "insightflow_wh"),
    "password": os.environ["PG_PASSWORD"],
}

# Metabase database registration — connects via Docker service name
METABASE_DB_NAME = os.getenv("METABASE_DB_NAME", "InsightFlow Warehouse")
METABASE_DB_DETAILS = {
    "host":     os.getenv("METABASE_DB_HOST",     "postgres-warehouse"),
    "port":     int(os.getenv("METABASE_DB_PORT", "5432")),
    "dbname":   os.getenv("METABASE_DB_DATABASE", "insightflow_warehouse"),
    "user":     os.getenv("METABASE_DB_USER",     "insightflow_wh"),
    "password": os.environ["METABASE_DB_PASSWORD"],
    "ssl":      False,
}


# ── Chart style ───────────────────────────────────────────────────────────────

COLOUR_BLUE       = "#1A56DB"
COLOUR_BLUE_LIGHT = "#3B82F6"


# ── Reusable Metabase building blocks ─────────────────────────────────────────

# Optional date-range filter injected into time-series queries via template tags
DATE_FILTER_SNIPPET = (
    "[[AND {col} >= SPLIT_PART({{{{date_range}}}},'~',1)::date]] "
    "[[AND {col} <= SPLIT_PART({{{{date_range}}}},'~',2)::date]]"
)

# GHS currency format applied to monetary columns
GHS_COLUMN_FORMAT = {
    "number_style":   "currency",
    "currency":       "GHS",
    "currency_style": "code",
    "decimals":       2,
}


def ghs_column_settings(*column_labels: str) -> dict:
    """Return column_settings dict applying GHS currency format to the given labels."""
    return {f'["name","{label}"]': GHS_COLUMN_FORMAT for label in column_labels}


# Template tag shared by all cards that support date filtering
DATE_TEMPLATE_TAG = {
    "date_range": {
        "id": "tt_dr", "name": "date_range",
        "display-name": "Date Range", "type": "text", "required": False,
    }
}


def date_parameter_mapping(card_id: int) -> list:
    """Wire the dashboard Date Range filter to a card's date_range template tag."""
    return [{"parameter_id": "p_date_range", "card_id": card_id,
             "target": ["variable", ["template-tag", "date_range"]]}]


# Dashboard-level filter widget definition
DASHBOARD_PARAMETERS = [
    {"id": "p_date_range", "type": "date/range",
     "name": "Date Range", "slug": "date_range", "sectionId": "date"}
]


# ── SQL Views ─────────────────────────────────────────────────────────────────
# Pre-aggregate the star schema so each card runs a simple SELECT on a view.
# Separated by blank lines so create_views() can execute them one at a time.

VIEWS_SQL = """
CREATE OR REPLACE VIEW v_kpi_summary AS
SELECT
    SUM(f.total_amount)            AS total_revenue,
    COUNT(f.sale_key)              AS total_transactions,
    COUNT(DISTINCT f.customer_key) AS unique_customers,
    SUM(f.quantity)                AS total_units_sold,
    ROUND(AVG(f.total_amount), 2)  AS avg_order_value
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key

CREATE OR REPLACE VIEW v_daily_revenue AS
SELECT
    d.full_date          AS date,
    SUM(f.total_amount)  AS daily_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.full_date
ORDER BY d.full_date

CREATE OR REPLACE VIEW v_monthly_revenue AS
SELECT
    MAKE_DATE(d.year, d.month, 1) AS month_start,
    SUM(f.total_amount)           AS monthly_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month
ORDER BY d.year, d.month

CREATE OR REPLACE VIEW v_weekly_summary AS
SELECT
    MIN(d.full_date)               AS week_start,
    MAX(d.full_date)               AS week_end,
    SUM(f.total_amount)            AS weekly_revenue,
    COUNT(f.sale_key)              AS transactions,
    COUNT(DISTINCT f.customer_key) AS unique_customers,
    SUM(f.quantity)                AS units_sold,
    ROUND(AVG(f.total_amount), 2)  AS avg_order_value
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.week_of_year
ORDER BY d.year, d.week_of_year
"""


# ── Dashboard cards (24-column grid) ──────────────────────────────────────────
#  Row  0–4  : 5 KPI scalars
#  Row  5–13 : Daily trend line (16 cols) | Monthly bar chart (8 cols)
#  Row 14–23 : Weekly summary table (24 cols)

DASHBOARD_CARDS = [
    # KPI scalars
    {"name": "Sales – Total Revenue",    "display": "scalar",
     "sql":  'SELECT ROUND(total_revenue,2) AS "Total Revenue (GHS)" FROM v_kpi_summary;',
     "viz":  {"card.title": "Total Revenue", "card.description": "All-time cumulative revenue",
              "scalar.decimals": 2, "column_settings": ghs_column_settings("Total Revenue (GHS)")},
     "col": 0,  "row": 0, "size_x": 5, "size_y": 5},

    {"name": "Sales – Transactions",     "display": "scalar",
     "sql":  'SELECT total_transactions AS "Transactions" FROM v_kpi_summary;',
     "viz":  {"card.title": "Transactions", "card.description": "Completed sales orders"},
     "col": 5,  "row": 0, "size_x": 5, "size_y": 5},

    {"name": "Sales – Unique Customers", "display": "scalar",
     "sql":  'SELECT unique_customers AS "Customers" FROM v_kpi_summary;',
     "viz":  {"card.title": "Unique Customers", "card.description": "Distinct buyers"},
     "col": 10, "row": 0, "size_x": 5, "size_y": 5},

    {"name": "Sales – Units Sold",       "display": "scalar",
     "sql":  'SELECT total_units_sold AS "Units Sold" FROM v_kpi_summary;',
     "viz":  {"card.title": "Units Sold", "card.description": "Total product units dispatched"},
     "col": 15, "row": 0, "size_x": 4, "size_y": 5},

    {"name": "Sales – Avg Order Value",  "display": "scalar",
     "sql":  'SELECT avg_order_value AS "Avg Order (GHS)" FROM v_kpi_summary;',
     "viz":  {"card.title": "Avg Order Value", "card.description": "Mean spend per transaction",
              "scalar.decimals": 2, "column_settings": ghs_column_settings("Avg Order (GHS)")},
     "col": 19, "row": 0, "size_x": 5, "size_y": 5},

    # Trend charts
    {"name": "Sales – Daily Revenue Trend", "display": "line",
     "sql":  ("SELECT date, daily_revenue AS \"Revenue (GHS)\" FROM v_daily_revenue WHERE 1=1 "
              + DATE_FILTER_SNIPPET.format(col="date") + " ORDER BY date;"),
     "tags": DATE_TEMPLATE_TAG, "filters": date_parameter_mapping,
     "viz":  {"graph.dimensions": ["date"], "graph.metrics": ["Revenue (GHS)"],
              "graph.x_axis.title_text": "Date", "graph.y_axis.title_text": "Revenue (GHS)",
              "graph.colors": [COLOUR_BLUE], "graph.label_value_frequency": "fit",
              "card.title": "Daily Revenue Trend",
              "card.description": "Revenue per day — zoom with the Date Range filter",
              "column_settings": ghs_column_settings("Revenue (GHS)")},
     "col": 0, "row": 5, "size_x": 16, "size_y": 9},

    {"name": "Sales – Monthly Revenue",  "display": "bar",
     "sql":  ("SELECT TO_CHAR(month_start,'Mon YYYY') AS \"Month\","
              "monthly_revenue AS \"Revenue (GHS)\" FROM v_monthly_revenue "
              "WHERE month_start < DATE_TRUNC('month', CURRENT_DATE) "
              + DATE_FILTER_SNIPPET.format(col="month_start") + " ORDER BY month_start;"),
     "tags": DATE_TEMPLATE_TAG, "filters": date_parameter_mapping,
     "viz":  {"graph.dimensions": ["Month"], "graph.metrics": ["Revenue (GHS)"],
              "graph.x_axis.title_text": "Month", "graph.y_axis.title_text": "Revenue (GHS)",
              "graph.colors": [COLOUR_BLUE_LIGHT], "graph.label_value_frequency": "fit",
              "card.title": "Revenue by Month",
              "card.description": "Monthly totals — current month excluded",
              "column_settings": ghs_column_settings("Revenue (GHS)")},
     "col": 16, "row": 5, "size_x": 8, "size_y": 9},

    # Weekly summary table
    {"name": "Sales – Weekly Summary",   "display": "table",
     "sql":  ("SELECT week_start AS \"Week Start\", week_end AS \"Week End\", "
              "weekly_revenue AS \"Revenue (GHS)\", transactions AS \"Transactions\", "
              "unique_customers AS \"Unique Customers\", units_sold AS \"Units Sold\", "
              "avg_order_value AS \"Avg Order (GHS)\" FROM v_weekly_summary WHERE 1=1 "
              + DATE_FILTER_SNIPPET.format(col="week_start") + " ORDER BY week_start DESC LIMIT 12;"),
     "tags": DATE_TEMPLATE_TAG, "filters": date_parameter_mapping,
     "viz":  {"card.title": "Weekly Performance",
              "card.description": "Last 12 weeks — revenue, orders, customers and units",
              "column_settings": ghs_column_settings("Revenue (GHS)", "Avg Order (GHS)")},
     "col": 0, "row": 14, "size_x": 24, "size_y": 10},
]


# ── HTTP session ──────────────────────────────────────────────────────────────
http_session    = requests.Session()
http_session.headers.update({"Content-Type": "application/json"})
REQUEST_TIMEOUT = 10  # seconds


# ── Functions ─────────────────────────────────────────────────────────────────

def wait_for_metabase() -> None:
    """Poll /api/health every 5 s until Metabase is ready (max 30 attempts)."""
    log.info("Waiting for Metabase...")
    for _ in range(30):
        try:
            if http_session.get(f"{METABASE_URL}/api/health", timeout=REQUEST_TIMEOUT).status_code == 200:
                log.info("Metabase is ready.")
                return
        except requests.exceptions.RequestException:
            pass
        time.sleep(5)
    raise RuntimeError("Metabase did not start in time.")


def login() -> str:
    """Authenticate and return the Metabase session token."""
    response = http_session.post(
        f"{METABASE_URL}/api/session",
        json={"username": METABASE_EMAIL, "password": METABASE_PASSWORD},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    log.info("Logged in as %s", METABASE_EMAIL)
    return response.json()["id"]


def create_views() -> None:
    """Drop and recreate all analytics views in PostgreSQL."""
    log.info("Creating views...")
    with psycopg2.connect(**POSTGRES_CONFIG) as pg_conn:
        pg_conn.autocommit = True
        with pg_conn.cursor() as cursor:
            for statement in re.split(r"\n\nCREATE OR REPLACE VIEW", VIEWS_SQL.strip()):
                statement = statement.strip()
                if not statement:
                    continue
                if not statement.upper().startswith("CREATE"):
                    statement = "CREATE OR REPLACE VIEW " + statement
                view_name = next((w for w in statement.split() if w.startswith("v_")), "?")
                try:
                    cursor.execute(f"DROP VIEW IF EXISTS {view_name} CASCADE;")
                    cursor.execute(statement + ";")
                    log.info("  [OK] %s", view_name)
                except Exception as error:
                    log.warning("  [WARN] %s: %s", view_name, error)
    time.sleep(3)


def get_or_create_database(session_id: str) -> int:
    """Register the warehouse database in Metabase if not already present, then sync."""
    headers = {"X-Metabase-Session": session_id}

    all_databases = http_session.get(
        f"{METABASE_URL}/api/database", headers=headers, timeout=REQUEST_TIMEOUT
    ).json()
    if isinstance(all_databases, dict):
        all_databases = all_databases.get("data", [])

    existing_db = next((db for db in all_databases if db["name"] == METABASE_DB_NAME), None)
    if existing_db:
        database_id = existing_db["id"]
        log.info("Database found (id=%s). Re-syncing...", database_id)
    else:
        response = http_session.post(
            f"{METABASE_URL}/api/database", headers=headers, timeout=REQUEST_TIMEOUT,
            json={"engine": "postgres", "name": METABASE_DB_NAME, "details": METABASE_DB_DETAILS},
        )
        response.raise_for_status()
        database_id = response.json()["id"]
        log.info("Database connected (id=%s).", database_id)

    http_session.post(
        f"{METABASE_URL}/api/database/{database_id}/sync_schema",
        headers=headers, timeout=REQUEST_TIMEOUT,
    ).raise_for_status()
    log.info("Syncing — waiting 20s...")
    time.sleep(20)
    return database_id


def clean_up(session_id: str) -> None:
    """Delete all existing cards and matching dashboards so the script is idempotent."""
    headers = {"X-Metabase-Session": session_id}

    existing_cards = http_session.get(
        f"{METABASE_URL}/api/card", headers=headers, timeout=REQUEST_TIMEOUT
    ).json() or []
    for card in existing_cards:
        http_session.delete(f"{METABASE_URL}/api/card/{card['id']}", headers=headers, timeout=REQUEST_TIMEOUT)
    if existing_cards:
        log.info("Removed %d old card(s).", len(existing_cards))

    for dashboard in http_session.get(
        f"{METABASE_URL}/api/dashboard", headers=headers, timeout=REQUEST_TIMEOUT
    ).json():
        if dashboard.get("name", "").startswith(DASHBOARD_NAME):
            http_session.delete(
                f"{METABASE_URL}/api/dashboard/{dashboard['id']}",
                headers=headers, timeout=REQUEST_TIMEOUT,
            )
            log.info("Removed dashboard: %s", dashboard["name"])


def build_dashboard(session_id: str, database_id: int) -> int:
    """Create the dashboard, add a tab, create all cards, and place them on the grid."""
    headers = {"X-Metabase-Session": session_id}

    dashboard_id = http_session.post(
        f"{METABASE_URL}/api/dashboard", headers=headers, timeout=REQUEST_TIMEOUT,
        json={"name": DASHBOARD_NAME, "parameters": DASHBOARD_PARAMETERS},
    ).json()["id"]
    log.info("Dashboard created (id=%s)", dashboard_id)

    tab_response = http_session.put(
        f"{METABASE_URL}/api/dashboard/{dashboard_id}", headers=headers, timeout=REQUEST_TIMEOUT,
        json={"tabs": [{"id": -1, "name": DASHBOARD_NAME}],
              "dashcards": [], "parameters": DASHBOARD_PARAMETERS},
    ).json()
    tab_id = (tab_response.get("tabs") or [{}])[0].get("id")

    dashcards = []
    for card_index, card_definition in enumerate(DASHBOARD_CARDS, start=1):
        native_query = {"query": card_definition["sql"]}
        if card_definition.get("tags"):
            native_query["template-tags"] = card_definition["tags"]

        card_response = http_session.post(
            f"{METABASE_URL}/api/card", headers=headers, timeout=REQUEST_TIMEOUT,
            json={"name": card_definition["name"], "display": card_definition["display"],
                  "dataset_query": {"type": "native", "native": native_query, "database": database_id},
                  "visualization_settings": card_definition.get("viz", {})},
        )
        if card_response.status_code not in (200, 202):
            log.warning("  [WARN] %s (%s)", card_definition["name"], card_response.status_code)
            continue

        card_id = card_response.json()["id"]
        dashcards.append({
            "id":               -card_index,  # negative = new dashcard
            "card_id":          card_id,
            "dashboard_tab_id": tab_id,
            "col":              card_definition["col"],
            "row":              card_definition["row"],
            "size_x":           card_definition["size_x"],
            "size_y":           card_definition["size_y"],
            "visualization_settings": card_definition.get("viz", {}),
            "parameter_mappings": (
                card_definition["filters"](card_id) if card_definition.get("filters") else []
            ),
        })
        log.info("  [OK] %s", card_definition["name"])

    placed_cards = http_session.put(
        f"{METABASE_URL}/api/dashboard/{dashboard_id}", headers=headers, timeout=REQUEST_TIMEOUT,
        json={"dashcards": dashcards, "tabs": tab_response.get("tabs", []),
              "parameters": DASHBOARD_PARAMETERS},
    ).json().get("dashcards", [])
    log.info("Placed %d cards.", len(placed_cards))
    return dashboard_id


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    wait_for_metabase()
    session_id   = login()
    create_views()
    database_id  = get_or_create_database(session_id)
    clean_up(session_id)
    dashboard_id = build_dashboard(session_id, database_id)
    log.info("Done → %s/dashboard/%s", METABASE_URL, dashboard_id)


if __name__ == "__main__":
    main()
