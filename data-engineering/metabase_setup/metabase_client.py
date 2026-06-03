# metabase_client.py

import logging
import re
import requests
import time
from config import METABASE_URL, MB_ADMIN_EMAIL, MB_ADMIN_PASSWORD, METABASE_DB_CONFIG

# ----------------------------
# Logging configuration
# ----------------------------
logger = logging.getLogger("MetabaseClient")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Shared session object
_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})

# ----------------------------
# Wait for Metabase
# ----------------------------
def wait_for_metabase(retries=30, interval=5):
    """Wait until Metabase API is ready."""
    for _ in range(retries):
        try:
            r = _session.get(f"{METABASE_URL}/api/health", timeout=10)
            if r.status_code == 200:
                logger.info("Metabase is ready.")
                return
        except requests.exceptions.RequestException:
            pass
        time.sleep(interval)
    raise RuntimeError("Metabase did not become ready in time.")

# ----------------------------
# Initial setup (fresh install)
# ----------------------------
def setup_metabase():
    """Run first-time Metabase setup if not already done."""
    r = _session.get(f"{METABASE_URL}/api/session/properties", timeout=10)
    r.raise_for_status()
    props = r.json()
    if props.get("has-user-setup"):
        return  # already set up
    setup_token = props.get("setup-token")
    payload = {
        "token": setup_token,
        "user": {
            "email": MB_ADMIN_EMAIL,
            "password": MB_ADMIN_PASSWORD,
            "first_name": "Admin",
            "last_name": "InsightFlow",
        },
        "prefs": {"site_name": "InsightFlow"},
    }
    r = _session.post(f"{METABASE_URL}/api/setup", json=payload, timeout=30)
    r.raise_for_status()
    logger.info("Metabase initial setup complete.")


# ----------------------------
# Login
# ----------------------------
def login():
    """Login to Metabase and return session ID."""
    r = _session.post(
        f"{METABASE_URL}/api/session",
        json={"username": MB_ADMIN_EMAIL, "password": MB_ADMIN_PASSWORD},
        timeout=10,
    )
    r.raise_for_status()
    session_id = r.json()["id"]
    logger.info("Login successful.")
    return session_id

# ----------------------------
# Connect or create database
# ----------------------------
def get_or_create_database(session_id):
    """Return the InsightFlow warehouse database ID, creating it in Metabase if needed."""
    headers = {"X-Metabase-Session": session_id}
    target_name = METABASE_DB_CONFIG["name"]

    r = _session.get(f"{METABASE_URL}/api/database", headers=headers, timeout=10)
    r.raise_for_status()
    response = r.json()
    db_list = response.get("data", response) if isinstance(response, dict) else response

    for db in db_list:
        if db.get("name") == target_name:
            logger.info(f"Found existing database '{target_name}' (ID: {db['id']})")
            return db["id"]

    # Not found — register the warehouse
    payload = {
        "engine": METABASE_DB_CONFIG["engine"],
        "name": target_name,
        "details": METABASE_DB_CONFIG["details"],
    }
    r = _session.post(f"{METABASE_URL}/api/database", json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    db_id = r.json()["id"]
    logger.info(f"Registered database '{target_name}' (ID: {db_id})")
    return db_id

# ----------------------------
# Cleanup dashboards and cards
# ----------------------------
def clean_up(session_id):
    """Delete all existing dashboards and cards."""
    headers = {"X-Metabase-Session": session_id}
    for endpoint in ["card", "dashboard"]:
        r = _session.get(f"{METABASE_URL}/api/{endpoint}", headers=headers, timeout=10)
        r.raise_for_status()
        resp = r.json()
        items = resp.get("data", resp) if isinstance(resp, dict) else resp
        for item in items or []:
            _session.delete(f"{METABASE_URL}/api/{endpoint}/{item['id']}", headers=headers, timeout=10)
    logger.info("Cleaned up old dashboards and cards.")

# ----------------------------
# Build tabbed dashboard
# ----------------------------
def build_tabbed_dashboard(session_id, db_id, tabs, name="InsightFlow Analytics", parameters=None):
    """Create one dashboard with multiple tabs, each with its own cards."""
    headers = {"X-Metabase-Session": session_id}

    # 1. Create the dashboard
    r = _session.post(
        f"{METABASE_URL}/api/dashboard",
        json={"name": name},
        headers=headers,
        timeout=10,
    )
    r.raise_for_status()
    dashboard_id = r.json()["id"]

    if not db_id:
        raise RuntimeError("Cannot build dashboard: database ID is None. Check WAREHOUSE_DB_* config.")

    # 2. Create all cards first, tracking which tab each belongs to
    mb_tabs = []       # tab definitions with temporary negative IDs
    all_dashcards = []
    card_index = 0

    for tab_index, (tab_name, cards) in enumerate(tabs):
        tab_temp_id = -(tab_index + 1)
        mb_tabs.append({"id": tab_temp_id, "name": tab_name})

        tab_card_count = 0
        for card_def in cards:
            clean_sql = re.sub(r'\[\[.*?\]\]', '', card_def["sql"], flags=re.DOTALL).strip()
            payload = {
                "name": card_def["name"],
                "display": card_def["display"],
                "dataset_query": {
                    "type": "native",
                    "native": {"query": clean_sql},
                    "database": db_id,
                },
                "visualization_settings": {},
            }
            r = _session.post(f"{METABASE_URL}/api/card", json=payload, headers=headers, timeout=10)
            if r.status_code not in (200, 202):
                logger.warning(f"  [FAIL] card '{card_def['name']}' (status {r.status_code}): {r.text[:200]}")
                continue
            card_index += 1
            tab_card_count += 1
            all_dashcards.append({
                "id": -card_index,
                "card_id": r.json()["id"],
                "dashboard_tab_id": tab_temp_id,
                "col": card_def.get("col", 0),
                "row": card_def.get("row", 0),
                "size_x": card_def.get("size_x", 6),
                "size_y": card_def.get("size_y", 4),
                "series": [],
                "parameter_mappings": [],
                "visualization_settings": {},
            })
        logger.info(f"Tab '{tab_name}' — {tab_card_count} cards created.")

    # 3. Attach tabs + dashcards + filters in a single PUT
    # Normalise parameters: add slug and sectionId required by Metabase API
    _section_map = {"date/range": "date", "date/single": "date", "string/=": "string", "number/=": "number"}
    mb_params = []
    for p in (parameters or []):
        mb_params.append({
            "id":        p["id"],
            "name":      p["name"],
            "type":      p["type"],
            "slug":      p["id"].replace("p_", ""),
            "sectionId": _section_map.get(p["type"], "string"),
        })

    r = _session.put(
        f"{METABASE_URL}/api/dashboard/{dashboard_id}",
        json={"tabs": mb_tabs, "dashcards": all_dashcards, "parameters": mb_params},
        headers=headers,
        timeout=30,
    )
    if r.status_code not in (200, 202):
        logger.warning(f"Failed to attach cards/tabs to dashboard: {r.text[:300]}")

    logger.info(f"Dashboard '{name}' created with {len(tabs)} tabs and {card_index} cards. ID: {dashboard_id}")
    return dashboard_id

# ----------------------------
# Set dashboard as homepage
# ----------------------------
def set_homepage(session_id, dashboard_id):
    """Pin the dashboard as the Metabase homepage for all users."""
    headers = {"X-Metabase-Session": session_id}
    # Try both payload formats across Metabase versions
    for payload in [{"value": {"dashboard_id": dashboard_id}}, {"value": dashboard_id}]:
        r = _session.put(
            f"{METABASE_URL}/api/setting/custom-homepage",
            json=payload,
            headers=headers,
            timeout=10,
        )
        if r.status_code in (200, 202):
            logger.info(f"Homepage set → {METABASE_URL}/dashboard/{dashboard_id}")
            return
    logger.info(f"Homepage auto-set not supported by this Metabase version. Access dashboard at: {METABASE_URL}/dashboard/{dashboard_id}")


# ----------------------------
# Create filter value cards
# ----------------------------
def create_filter_value_cards(session_id, db_id):
    """
    Create filter value cards for dashboard interactivity.
    Returns dictionary of card IDs.
    """
    headers = {"X-Metabase-Session": session_id}
    value_card_ids = {}

    FILTER_CARDS = [
        {"key": "country_values", "name": "Country Filter",
         "sql": "SELECT DISTINCT country FROM v_country_comparison ORDER BY country;"},
        {"key": "region_values", "name": "Region Filter",
         "sql": "SELECT DISTINCT region_name FROM v_regional_comparison ORDER BY region_name;"},
        {"key": "category_values", "name": "Category Filter",
         "sql": "SELECT DISTINCT \"categoryName\" FROM v_product_revenue ORDER BY \"categoryName\";"}
    ]

    for fvc in FILTER_CARDS:
        payload = {
            "name": fvc["name"],
            "display": "table",
            "dataset_query": {"type": "native", "native": {"query": fvc["sql"]}, "database": db_id},
            "visualization_settings": {}
        }
        r = _session.post(f"{METABASE_URL}/api/card", json=payload, headers=headers, timeout=10)
        if r.status_code in (200, 202):
            value_card_ids[fvc["key"]] = int(r.json()["id"])
            logger.info(f"Filter card created: {fvc['name']} (ID: {value_card_ids[fvc['key']]})")

    return value_card_ids