"""Data lineage tracking for the InsightFlow ETL pipeline.

Architecture
------------
``LineageStage``
    String constants for each stage of the pipeline:
    EXTRACT → QUALITY_CHECK → CLEANSE → LOAD_DIMENSION → LOAD_FACT → REPORTING.
    Used to tag ``LineageEvent.stage`` so events can be sorted into pipeline
    order and grouped by stage in reports.

``LineageEvent``
    Immutable record of a single data-movement step.  In addition to the
    original fields (source/target tables, row counts, quality score) it now
    carries three optional metadata fields:

    ``stage``         — one of the ``LineageStage`` constants
    ``data_source``   — logical source label (``"pos"``, ``"online_orders"``, …)
    ``rows_filtered`` — rows dropped or skipped at this step

    All new fields default to empty/zero so existing callers (e.g. in
    ``etl/load.py``) require no changes.

``LineageTracker``
    Accumulates events for a single pipeline run.  Provides:

    Convenience recorders — ``record_extraction``, ``record_quality``,
    ``record_cleanse`` — one per pipeline stage, each stamping the correct
    ``stage`` and ``data_source`` so downstream helpers can reconstruct the
    full journey.

    Query helpers — ``get_lineage_chain(data_source)`` returns events for one
    source in pipeline order; ``to_report()`` returns a grouped summary dict.

    Persistence — ``save()`` writes the raw event log as
    ``lineage_<run_id>.json``; ``save_report()`` writes the grouped summary as
    ``lineage_report_<run_id>.json``.

Usage
-----
    tracker = LineageTracker(run_id="abc-123")

    tracker.record_extraction("pos", rows=5_000, since=date(2024, 1, 1))
    tracker.record_quality("pos", quality_report)          # SourceQualityReport
    tracker.record_cleanse("pos", rows_before=5_000,
                           rows_after=4_980,
                           transformations=["drop_null_sku", "clamp_discount"])
    # … Loader records LOAD_FACT events via tracker.record() …

    tracker.save(lineage_dir)         # lineage_abc-123.json
    tracker.save_report(lineage_dir)  # lineage_report_abc-123.json
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from etl.quality import SourceQualityReport

log = logging.getLogger("insightflow.lineage")


# ---------------------------------------------------------------------------
# Pipeline stage constants
# ---------------------------------------------------------------------------


class LineageStage:
    """String constants for the ETL pipeline stages.

    Use these to tag ``LineageEvent.stage`` so ``get_lineage_chain()`` can
    sort events into pipeline order and reports can group by stage.

    Stages in execution order
    -------------------------
    EXTRACT         — raw data pulled from the OLTP source database.
    QUALITY_CHECK   — rule-based and statistical quality validation.
    CLEANSE         — business-rule cleansing (null drops, clamps, recomputes).
    LOAD_DIMENSION  — dimension table upserts in the OLAP warehouse.
    LOAD_FACT       — fact table inserts in the OLAP warehouse.
    REPORTING       — downstream aggregations or report refreshes.
    """

    EXTRACT = "extract"
    QUALITY_CHECK = "quality_check"
    CLEANSE = "cleanse"
    LOAD_DIMENSION = "load_dimension"
    LOAD_FACT = "load_fact"
    REPORTING = "reporting"

    _ORDER = [EXTRACT, QUALITY_CHECK, CLEANSE, LOAD_DIMENSION, LOAD_FACT, REPORTING]


# ---------------------------------------------------------------------------
# Lineage event
# ---------------------------------------------------------------------------


@dataclass
class LineageEvent:
    """Record of a single data-movement step in the ETL pipeline.

    Attributes
    ----------
    run_id:
        UUID of the pipeline run that produced this event.
    step:
        Human-readable step label, e.g. ``"extract_pos"``.
    source_table:
        Name of the table or logical dataset being read.
    target_table:
        Name of the table or logical dataset being written.
    source_db:
        Source database identifier (e.g. ``"insightflow_app"``).
    target_db:
        Target database identifier (e.g. ``"insightflow_star_schema"``).
    rows_extracted:
        Number of rows read from the source.
    rows_loaded:
        Number of rows written to the target.
    quality_score:
        Fraction of rows that passed all quality checks at this step (0–1).
    filters_applied:
        Filter conditions applied (e.g. ``["since=2024-01-01"]``).
    transformations:
        Transformation descriptions applied at this step.
    stage:
        One of the ``LineageStage`` string constants.  Empty string = stage
        unspecified (backward-compatible default for existing callers).
    data_source:
        Logical source identifier: ``"pos"``, ``"online_orders"``,
        ``"feedback"``, or ``"inventory"``.  Empty = unspecified.
    rows_filtered:
        Rows dropped or skipped at this step
        (typically ``rows_extracted - rows_loaded``).
    timestamp:
        UTC ISO timestamp when the event was recorded.
    """

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
    stage: str = ""
    data_source: str = ""
    rows_filtered: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------


class LineageTracker:
    """Accumulate ``LineageEvent`` objects for a single pipeline run.

    All ``record_*`` convenience methods stamp the correct ``stage`` and
    ``data_source`` so ``get_lineage_chain()`` can reconstruct the full
    source-to-warehouse journey.

    Parameters
    ----------
    run_id:
        UUID that uniquely identifies this pipeline run.
    """

    _SOURCE_DB = "insightflow_app"
    _WAREHOUSE_DB = "insightflow_star_schema"

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._events: list[LineageEvent] = []

    # ------------------------------------------------------------------
    # Core recorder
    # ------------------------------------------------------------------

    def record(self, event: LineageEvent) -> None:
        """Append a lineage event."""
        self._events.append(event)
        log.debug(
            "Lineage recorded: stage=%s step=%s %s→%s "
            "rows_extracted=%d rows_loaded=%d rows_filtered=%d",
            event.stage or "?",
            event.step,
            event.source_table,
            event.target_table,
            event.rows_extracted,
            event.rows_loaded,
            event.rows_filtered,
        )

    # ------------------------------------------------------------------
    # Convenience recorders — one per pipeline stage
    # ------------------------------------------------------------------

    def record_extraction(
        self,
        data_source: str,
        rows: int,
        since: Any = None,
    ) -> None:
        """Record an EXTRACT-stage event.

        Parameters
        ----------
        data_source:
            Logical source name (``"pos"``, ``"online_orders"``, …).
        rows:
            Number of rows extracted.
        since:
            Incremental watermark date, or None for a full load.
        """
        filters = [f"since={since}"] if since is not None else ["full_load"]
        self.record(
            LineageEvent(
                run_id=self.run_id,
                step=f"extract_{data_source}",
                stage=LineageStage.EXTRACT,
                data_source=data_source,
                source_table=data_source,
                target_table="DataFrame",
                source_db=self._SOURCE_DB,
                target_db="memory",
                rows_extracted=rows,
                rows_loaded=rows,
                quality_score=1.0,
                filters_applied=filters,
            )
        )

    def record_quality(
        self,
        data_source: str,
        report: "SourceQualityReport",
    ) -> None:
        """Record a QUALITY_CHECK-stage event from a ``SourceQualityReport``.

        Parameters
        ----------
        data_source:
            Logical source name.
        report:
            Quality report produced by ``DataQualityChecker.score_source()``.
        """
        self.record(
            LineageEvent(
                run_id=self.run_id,
                step=f"quality_{data_source}",
                stage=LineageStage.QUALITY_CHECK,
                data_source=data_source,
                source_table=f"{data_source}_raw",
                target_table=f"{data_source}_validated",
                source_db="memory",
                target_db="memory",
                rows_extracted=report.total_rows,
                rows_loaded=report.passed_rows,
                rows_filtered=report.failed_rows,
                quality_score=report.overall_score,
                transformations=[f"rule:{r}" for r in report.rule_scores],
            )
        )

    def record_cleanse(
        self,
        data_source: str,
        rows_before: int,
        rows_after: int,
        transformations: list[str],
    ) -> None:
        """Record a CLEANSE-stage event.

        Parameters
        ----------
        data_source:
            Logical source name.
        rows_before:
            Row count entering the cleanse step.
        rows_after:
            Row count after cleansing (nulls dropped, values clamped, etc.).
        transformations:
            Human-readable list of transformations applied.
        """
        self.record(
            LineageEvent(
                run_id=self.run_id,
                step=f"cleanse_{data_source}",
                stage=LineageStage.CLEANSE,
                data_source=data_source,
                source_table=f"{data_source}_validated",
                target_table=f"{data_source}_cleansed",
                source_db="memory",
                target_db="memory",
                rows_extracted=rows_before,
                rows_loaded=rows_after,
                rows_filtered=rows_before - rows_after,
                quality_score=rows_after / max(rows_before, 1),
                transformations=transformations,
            )
        )

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_lineage_chain(self, data_source: str) -> list[LineageEvent]:
        """Return all events for *data_source* sorted by pipeline stage order.

        Events with unrecognised stages appear at the end.

        Parameters
        ----------
        data_source:
            Logical source name (e.g. ``"pos"``).

        Returns
        -------
        list[LineageEvent]
            Events in pipeline order:
            EXTRACT → QUALITY_CHECK → CLEANSE → LOAD_DIMENSION →
            LOAD_FACT → REPORTING.
        """

        def _sort_key(event: LineageEvent) -> int:
            try:
                return LineageStage._ORDER.index(event.stage)
            except ValueError:
                return len(LineageStage._ORDER)

        return sorted(
            (e for e in self._events if e.data_source == data_source),
            key=_sort_key,
        )

    def to_report(self) -> dict[str, Any]:
        """Return a structured lineage summary grouped by data source.

        Suitable for JSON serialisation and observability dashboards.

        Returns
        -------
        dict
            Keys: ``run_id``, ``sources`` (per-source event lists),
            ``total_events``, ``generated_at``.
        """
        sources: dict[str, list[dict[str, Any]]] = {}
        for event in self._events:
            src = event.data_source or "unknown"
            sources.setdefault(src, []).append(
                {
                    "stage": event.stage or "unspecified",
                    "step": event.step,
                    "source_table": event.source_table,
                    "target_table": event.target_table,
                    "rows_extracted": event.rows_extracted,
                    "rows_loaded": event.rows_loaded,
                    "rows_filtered": event.rows_filtered,
                    "quality_score": round(event.quality_score, 4),
                    "transformations": event.transformations,
                    "timestamp": event.timestamp,
                }
            )
        return {
            "run_id": self.run_id,
            "sources": sources,
            "total_events": len(self._events),
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, output_dir: Path) -> Path:
        """Write ``lineage_<run_id>.json`` (full event log) to *output_dir*.

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

    def save_report(self, output_dir: Path) -> Path:
        """Write ``lineage_report_<run_id>.json`` (grouped summary) to *output_dir*.

        Groups events by data source for easier reading.  Call after
        ``save()`` to produce both artefacts from a single run.

        Returns the path of the written file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"lineage_report_{self.run_id}.json"
        out_path.write_text(
            json.dumps(self.to_report(), indent=2, default=str), encoding="utf-8"
        )
        log.info("Lineage report saved: %s", out_path)
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
            Step-level provenance for the given target table.  Row-level FK
            mappings are not recoverable retrospectively.
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
