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
