"""
Pytest configuration and fixtures for backend tests.
"""
import sys
import os
import django
from pathlib import Path

# Add backend directory to Python path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import pytest
from django.conf import settings


def pytest_configure():
    """Configure Django settings for pytest."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "insightflow.settings.dev")
    django.setup()


@pytest.fixture
def django_db_setup(django_db_setup, django_db_blocker):
    """Django database setup for tests."""
    with django_db_blocker.unblock():
        pass
