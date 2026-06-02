import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@amalitech.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password123")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def _docker_compose(*args: str) -> subprocess.CompletedProcess:
    """Run docker compose command, trying 'docker compose' then 'docker-compose'."""
    base_cmd = ["-f", str(COMPOSE_FILE)]
    for cmd in (["docker", "compose"], ["docker-compose"]):
        try:
            return subprocess.run(
                cmd + base_cmd + list(args),  # type: ignore[return-value]
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            continue
    raise RuntimeError(
        "Neither 'docker compose' nor 'docker-compose' was found. "
        "Install Docker Desktop and try again."
    )


@pytest.fixture(scope="session", autouse=True)
def django_server():
    """Ensure the backend is reachable before any test runs.

    If the server at ``API_BASE_URL`` (default: http://localhost:8080) is
    already up, this fixture is a no-op.  Otherwise it starts the stack with
    ``docker compose up -d postgres-app backend`` and tears it back down after
    the session.
    """
    parsed = urlparse(BASE_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8080

    if _port_open(host, port):
        yield  # already running — nothing to manage
        return

    # Try to start via Docker Compose
    try:
        _docker_compose("up", "-d", "postgres-app", "backend")
    except RuntimeError as exc:
        pytest.fail(str(exc))
    except subprocess.CalledProcessError as exc:
        pytest.fail(
            f"docker compose up failed (exit {exc.returncode}).\n"
            f"stderr:\n{exc.stderr}\n\n"
            "Make sure Docker Desktop is running and try again."
        )

    # Wait up to 60 s for the backend to accept HTTP connections
    deadline = time.time() + 60
    while time.time() < deadline:
        if _port_open(host, port):
            break
        time.sleep(2)
    else:
        _docker_compose("logs", "--tail", "50", "backend")
        pytest.fail(
            f"Backend did not become reachable at {host}:{port} within 60 s.\n"
            "Check container logs with: docker compose logs backend"
        )

    yield

    # Tear down only what we started
    try:
        _docker_compose("stop", "backend", "postgres-app")
    except (RuntimeError, subprocess.CalledProcessError):
        pass  # best-effort cleanup


# ---------------------------------------------------------------------------
# Common fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def admin_token(base_url):
    resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["token"]


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
