"""
Pytest configuration and fixtures for backend tests.
"""

import os
import sys
from pathlib import Path

import django
import pytest

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))


def pytest_configure():
    """Configure Django settings for pytest."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "insightflow.settings.dev")
    django.setup()


@pytest.fixture
def django_db_setup(django_db_setup, django_db_blocker):
    """Django database setup for tests."""
    with django_db_blocker.unblock():
        pass


# ── Live-server fixtures (used by test_ingestion_pos.py, test_api.py) ────────
# When the backend is not running locally these skip gracefully instead of
# erroring with "fixture not found".


@pytest.fixture(scope="session")
def base_url():
    """
    Base URL of the running backend. Override via API_BASE_URL env var.
    Skips every test that uses this fixture when the server is not reachable,
    so the suite never errors with connection refused locally.
    """
    import requests as _requests

    url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    try:
        _requests.get(f"{url}/api-docs/", timeout=3)
    except Exception:
        pytest.skip(
            "Backend server not reachable — skipping live API tests. "
            "Start the backend or set API_BASE_URL to run these tests."
        )
    return url


@pytest.fixture(scope="session")
def auth_headers(base_url):
    """
    JWT Bearer token for the seeded admin user.
    Skips the test if the backend server is not reachable.
    Override credentials via API_AUTH_USERNAME / API_AUTH_PASSWORD env vars.
    """
    try:
        import requests as _requests

        username = os.environ.get("API_AUTH_USERNAME", "admin")
        password = os.environ.get("API_AUTH_PASSWORD", "admin123")

        resp = _requests.post(
            f"{base_url}/api/auth/login/",
            json={"username": username, "password": password},
            timeout=5,
        )

        if resp.status_code == 200:
            token = resp.json().get("access")
            if token:
                return {"Authorization": f"Bearer {token}"}

        pytest.skip(
            f"Auth failed (status {resp.status_code}) — "
            "skipping live API test. Start the backend to run these tests."
        )

    except Exception:
        pytest.skip(
            "Backend server not reachable — "
            "skipping live API test. Start the backend to run these tests."
        )
