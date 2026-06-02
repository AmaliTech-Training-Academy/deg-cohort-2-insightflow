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
