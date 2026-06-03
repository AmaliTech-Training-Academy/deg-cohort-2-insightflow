"""Tests for etl.lineage — LineageTracker and LineageEvent."""

import json
from pathlib import Path

from etl.lineage import LineageEvent, LineageTracker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RUN_ID = "run-test-001"


def _make_event(
    run_id: str = _RUN_ID,
    target_table: str = "factSales",
) -> LineageEvent:
    """Return a minimal LineageEvent for testing."""
    return LineageEvent(
        run_id=run_id,
        step="load",
        source_table="posTransaction",
        target_table=target_table,
        source_db="insightflow_oltp",
        target_db="insightflow_star_schema",
        rows_extracted=5,
        rows_loaded=5,
        quality_score=1.0,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_lineage_event_recorded(tmp_path: Path) -> None:
    """Recording a LineageEvent must result in exactly one entry in _events."""
    tracker = LineageTracker(run_id=_RUN_ID)
    tracker.record(_make_event())
    assert len(tracker._events) == 1, f"Expected 1 event, got {len(tracker._events)}"


def test_lineage_saves_json(tmp_path: Path) -> None:
    """tracker.save(tmp_path) must create a JSON file with at least one event dict."""
    tracker = LineageTracker(run_id=_RUN_ID)
    tracker.record(_make_event())
    out_file = tracker.save(tmp_path)

    assert out_file.exists(), f"Expected lineage file at {out_file}"

    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert isinstance(payload, list), "Saved JSON must be a list of event dicts"
    assert len(payload) == 1, "Saved JSON must contain exactly one event"

    event_dict = payload[0]
    for key in ("run_id", "step", "source_table", "target_table"):
        assert key in event_dict, f"Event dict missing key: {key}"


def test_lineage_json_contains_run_id(tmp_path: Path) -> None:
    """Each saved event dict must carry the run_id embedded in LineageEvent."""
    run_id = "run-003"
    tracker = LineageTracker(run_id=run_id)
    tracker.record(_make_event(run_id=run_id))
    out_file = tracker.save(tmp_path)

    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert (
        payload[0]["run_id"] == run_id
    ), f"Expected run_id={run_id!r}, got {payload[0]['run_id']!r}"


def test_get_source_records_returns_dict_list(tmp_path: Path) -> None:
    """get_source_records must return a non-empty list for a matching target_table."""
    tracker = LineageTracker(run_id=_RUN_ID)
    tracker.record(_make_event(target_table="factSales"))
    # Also record an unrelated event that should not appear in results
    tracker.record(_make_event(target_table="factFeedback"))

    results = tracker.get_source_records("factSales", "TXN-001")
    assert isinstance(results, list), "get_source_records must return a list"
    assert len(results) > 0, "Expected at least one result for factSales"
    assert all(isinstance(r, dict) for r in results), "Each result must be a dict"
    # Verify the returned entry points to the correct source table
    assert results[0]["source_table"] == "posTransaction"
