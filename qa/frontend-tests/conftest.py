import os
import socket
from urllib.parse import urlparse

import pytest
from dotenv import load_dotenv

load_dotenv()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session", autouse=True)
def frontend_server():
    """Fail fast if the frontend dev server is not reachable."""
    parsed = urlparse(FRONTEND_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or 3000

    if not _port_open(host, port):
        pytest.fail(
            f"Frontend is not reachable at {FRONTEND_URL}. "
            "Run `npm run dev` inside the frontend/ directory first."
        )
    yield


@pytest.fixture(scope="session")
def base_url() -> str:
    return FRONTEND_URL


@pytest.fixture(scope="session")
def auth_storage_state(browser, base_url: str, tmp_path_factory) -> str:
    """
    Log in once for the entire test session and persist the browser storage
    state (localStorage token) to a temp file.  Every test that needs an
    authenticated page loads this state instead of going through the login
    form again — cuts login round-trips from N tests down to 1.
    """
    state_path = str(tmp_path_factory.mktemp("auth") / "state.json")

    context = browser.new_context()
    page = context.new_page()
    page.goto(f"{base_url}/login")
    page.fill("#email", "user@insightflow.io")
    page.fill("#password", "Password1!")
    page.click("button[type='submit']")
    page.wait_for_url(f"{base_url}/dashboard", timeout=10_000)

    context.storage_state(path=state_path)
    context.close()

    return state_path


@pytest.fixture
def auth_page(browser, auth_storage_state: str, base_url: str):
    """
    Yield a Page that is already authenticated.  Uses the saved storage state
    so no login form is submitted.  Closes the context after the test.
    """
    context = browser.new_context(storage_state=auth_storage_state)
    page = context.new_page()
    # The app reads the token from localStorage on mount — navigate to trigger
    # the auth check so the page renders fully before the test body runs.
    page.goto(f"{base_url}/dashboard")
    page.wait_for_selector("h1", timeout=10_000)
    yield page
    context.close()
