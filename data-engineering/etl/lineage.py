"""Data lineage tracking for the InsightFlow ETL pipeline."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("insightflow.lineage")


@dataclass
class LineageEvent:
    run_id: str
    step: str
    source_table: str
    target_table: str
    source_db: str
    target_db: str
    rows_extracted: int
    rows_loaded: int
    quality_score: float
    filters_applied: list[str] = field(default_factory=list)
    transformations: list[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )


class LineageTracker:
    """Accumulate LineageEvents for a single pipeline run and persist them."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._events: list[LineageEvent] = []

    def record(self, event: LineageEvent) -> None:
        """Append a lineage event."""
        self._events.append(event)
        log.debug(
            "Lineage recorded: step=%s %s→%s rows_extracted=%d rows_loaded=%d",
            event.step,
            event.source_table,
            event.target_table,
            event.rows_extracted,
            event.rows_loaded,
        )

    def save(self, output_dir: Path) -> Path:
        """Write ``lineage_<run_id>.json`` to *output_dir*.

        Returns the path of the written file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"lineage_{self.run_id}.json"
        payload = [asdict(e) for e in self._events]
        out_path.write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )
        log.info("Lineage saved: %s (%d events)", out_path, len(payload))
        return out_path

    def get_source_records(
        self, target_table: str, fact_key_value: Any
    ) -> list[dict[str, Any]]:
        """Return descriptions of source rows that contributed to a fact row.

        Parameters
        ----------
        target_table:
            The fact table name (e.g. ``"factSales"``).
        fact_key_value:
            The surrogate key value of the fact row being traced.

        Returns
        -------
        list[dict]
            Each dict has ``source_table``, ``sourceTransactionId``, and
            ``step``.  The lineage recorded at load time is used; this method
            cannot recover row-level FK mappings retrospectively, so it returns
            the step-level provenance for the given target table.
        """
        results: list[dict[str, Any]] = []
        for event in self._events:
            if event.target_table == target_table:
                results.append(
                    {
                        "source_table": event.source_table,
                        "sourceTransactionId": fact_key_value,
                        "step": event.step,
                        "run_id": event.run_id,
                        "source_db": event.source_db,
                        "target_db": event.target_db,
                        "timestamp": event.timestamp,
                    }
                )
        return results
