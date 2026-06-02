"""Tests for etl.state — watermark-based incremental load detection."""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

_DE_ROOT = Path(__file__).parent.parent.parent / "data-engineering"
if str(_DE_ROOT) not in sys.path:
    sys.path.insert(0, str(_DE_ROOT))

from etl.state import get_watermark_date  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_engine(scalar_return):
    """Build a mock engine whose execute().scalar() returns *scalar_return*."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = scalar_return

    mock_conn = MagicMock()
    mock_conn.execute.return_value = mock_result
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn
    return mock_engine


# ---------------------------------------------------------------------------
# get_watermark_date
# ---------------------------------------------------------------------------


def test_get_watermark_returns_none_when_warehouse_empty() -> None:
    """When no fact rows exist MAX(fullDate) is NULL — watermark must be None."""
    engine = _mock_engine(scalar_return=None)
    result = get_watermark_date(engine)
    assert result is None, "Empty warehouse should return None (triggers full load)"


def test_get_watermark_returns_date_when_data_present() -> None:
    """When fact rows exist, watermark must equal MAX(fullDate) from the warehouse."""
    expected = date(2024, 3, 18)
    engine = _mock_engine(scalar_return=expected)
    result = get_watermark_date(engine)
    assert result == expected, f"Expected watermark {expected}, got {result}"


def test_get_watermark_converts_datetime_to_date() -> None:
    """If the DB returns a datetime instead of a plain date it must be coerced."""
    from datetime import datetime, timezone

    dt = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    engine = _mock_engine(scalar_return=dt)
    result = get_watermark_date(engine)
    assert isinstance(result, date), "Result must be a date, not a datetime"
    assert result == date(2024, 6, 1)


def test_get_watermark_returns_none_on_db_error() -> None:
    """A DB exception during watermark query must be caught and return None."""
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = Exception("connection lost")
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn

    # Patch the module logger to avoid WSL Python 3.12 logging segfault
    # that occurs when log.warning() is called in an exception context.
    with patch("etl.state.log"):
        result = get_watermark_date(mock_engine)

    assert result is None, "DB error during watermark query must not raise"


# ---------------------------------------------------------------------------
# Incremental flow contract
# ---------------------------------------------------------------------------


def test_full_load_on_first_run() -> None:
    """First run (empty warehouse) must produce since=None to load all records."""
    engine = _mock_engine(scalar_return=None)
    since = get_watermark_date(engine)
    assert since is None, "On first run since must be None so ETL extracts everything"


def test_incremental_load_after_data_exists() -> None:
    """After data is loaded, watermark must be non-None to prevent a full reload."""
    engine = _mock_engine(scalar_return=date(2024, 3, 10))
    since = get_watermark_date(engine)
    assert since is not None, "With warehouse data present, since must not be None"
    assert since == date(2024, 3, 10), "since must equal the watermark date"
