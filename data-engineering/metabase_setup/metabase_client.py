# metabase_client.py
# All Metabase REST API interactions
import logging
import time
from typing import Callable, Optional

import requests
from config import MB_ADMIN_EMAIL, MB_ADMIN_PASSWORD, METABASE_DB_CONFIG, METABASE_URL

log = logging.getLogger("insightflow")

DASHBOARD_NAME = "InsightFlow Analytics"
REQUEST_TIMEOUT = 10  # seconds per API request

# Dashboard-level Date Range filter widget shared by all time-series cards
DASHBOARD_PARAMETERS = [
    {
        "id": "p_date_range",
        "type": "date/range",
        "name": "Date Range",
        "slug": "date_range",
        "sectionId": "date",
    }
]

# Shared HTTP session — reuses connections across all API calls
_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})


def wait_for_metabase() -> None:
    """Poll /api/health every 5 s until Metabase is ready (max 30 attempts)."""
    log.info("Waiting for Metabase...")
    for _ in range(30):
        try:
            if (
                _session.get(
                    f"{METABASE_URL}/api/health", timeout=REQUEST_TIMEOUT
                ).status_code
                == 200
            ):
                log.info("Metabase is ready.")
                return
        except requests.exceptions.RequestException:
            pass
        time.sleep(5)
    raise RuntimeError("Metabase did not start in time.")


def login() -> str:
    """Authenticate and return the Metabase session token."""
    response = _session.post(
        f"{METABASE_URL}/api/session",
        json={"username": MB_ADMIN_EMAIL, "password": MB_ADMIN_PASSWORD},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    log.info("Logged in as %s", MB_ADMIN_EMAIL)
    return str(response.json()["id"])


def get_or_create_database(session_id: str) -> int:
    """Register the warehouse database in Metabase if not already present, then sync."""
    headers = {"X-Metabase-Session": session_id}
    db_name = METABASE_DB_CONFIG["name"]

    all_databases = _session.get(
        f"{METABASE_URL}/api/database", headers=headers, timeout=REQUEST_TIMEOUT
    ).json()
    if isinstance(all_databases, dict):
        all_databases = all_databases.get("data", [])

    existing: Optional[dict] = next(
        (db for db in all_databases if db["name"] == db_name), None
    )
    if existing:
        database_id = int(existing["id"])
        log.info("Database found (id=%s). Re-syncing...", database_id)
    else:
        response = _session.post(
            f"{METABASE_URL}/api/database",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            json=METABASE_DB_CONFIG,
        )
        response.raise_for_status()
        database_id = int(response.json()["id"])
        log.info("Database connected (id=%s).", database_id)

    _session.post(
        f"{METABASE_URL}/api/database/{database_id}/sync_schema",
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    ).raise_for_status()
    log.info("Syncing — waiting 20s...")
    time.sleep(20)
    return database_id


def clean_up(session_id: str) -> None:
    """Delete all existing cards and matching dashboards so the script is idempotent."""
    headers = {"X-Metabase-Session": session_id}

    existing_cards = (
        _session.get(
            f"{METABASE_URL}/api/card", headers=headers, timeout=REQUEST_TIMEOUT
        ).json()
        or []
    )
    for card in existing_cards:
        _session.delete(
            f"{METABASE_URL}/api/card/{card['id']}",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
    if existing_cards:
        log.info("Removed %d old card(s).", len(existing_cards))

    for dashboard in _session.get(
        f"{METABASE_URL}/api/dashboard", headers=headers, timeout=REQUEST_TIMEOUT
    ).json():
        if dashboard.get("name", "").startswith(DASHBOARD_NAME):
            _session.delete(
                f"{METABASE_URL}/api/dashboard/{dashboard['id']}",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            log.info("Removed dashboard: %s", dashboard["name"])


def build_dashboard(session_id: str, database_id: int, cards: list[dict]) -> int:
    """Create the dashboard, add a tab, create all cards, and place them on the grid."""
    headers = {"X-Metabase-Session": session_id}

    dashboard_id = int(
        _session.post(
            f"{METABASE_URL}/api/dashboard",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            json={"name": DASHBOARD_NAME, "parameters": DASHBOARD_PARAMETERS},
        ).json()["id"]
    )
    log.info("Dashboard created (id=%s)", dashboard_id)

    tab_response = _session.put(
        f"{METABASE_URL}/api/dashboard/{dashboard_id}",
        headers=headers,
        timeout=REQUEST_TIMEOUT,
        json={
            "tabs": [{"id": -1, "name": DASHBOARD_NAME}],
            "dashcards": [],
            "parameters": DASHBOARD_PARAMETERS,
        },
    ).json()
    tab_id = (tab_response.get("tabs") or [{}])[0].get("id")

    dashcards = []
    for card_index, card_definition in enumerate(cards, start=1):
        native_query: dict = {"query": card_definition["sql"]}
        if card_definition.get("tags"):
            native_query["template-tags"] = card_definition["tags"]

        card_response = _session.post(
            f"{METABASE_URL}/api/card",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            json={
                "name": card_definition["name"],
                "display": card_definition["display"],
                "dataset_query": {
                    "type": "native",
                    "native": native_query,
                    "database": database_id,
                },
                "visualization_settings": card_definition.get("viz", {}),
            },
        )
        if card_response.status_code not in (200, 202):
            log.warning(
                "  [WARN] %s (%s)", card_definition["name"], card_response.status_code
            )
            continue

        card_id = int(card_response.json()["id"])
        filter_fn: Optional[Callable[[int], list]] = card_definition.get("filters")
        dashcards.append(
            {
                "id": -card_index,
                "card_id": card_id,
                "dashboard_tab_id": tab_id,
                "col": card_definition["col"],
                "row": card_definition["row"],
                "size_x": card_definition["size_x"],
                "size_y": card_definition["size_y"],
                "visualization_settings": card_definition.get("viz", {}),
                "parameter_mappings": filter_fn(card_id) if filter_fn else [],
            }
        )
        log.info("  [OK] %s", card_definition["name"])

    placed = (
        _session.put(
            f"{METABASE_URL}/api/dashboard/{dashboard_id}",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            json={
                "dashcards": dashcards,
                "tabs": tab_response.get("tabs", []),
                "parameters": DASHBOARD_PARAMETERS,
            },
        )
        .json()
        .get("dashcards", [])
    )
    log.info("Placed %d cards.", len(placed))
    return dashboard_id
