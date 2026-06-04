"""Anomaly alerting module for the InsightFlow ETL pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from etl.quality import QUALITY_THRESHOLDS

log = logging.getLogger("insightflow.alerts")


@dataclass
class AnomalyAlert:
    table: str
    rule: str
    affected_rows: int
    sample_values: list[Any]
    severity: str  # "WARNING" | "CRITICAL"
    detected_at: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )


class AlertManager:
    """Collect, log, and flush anomaly alerts."""

    def __init__(self) -> None:
        self._alerts: list[AnomalyAlert] = []

    def add(self, alert: AnomalyAlert) -> None:
        """Store a new alert."""
        self._alerts.append(alert)

    def flush(self, quality_summary: dict[str, Any]) -> None:
        """Log all collected alerts and raise on CRITICAL quality.

        The overall severity is CRITICAL when the overall_score falls below the
        threshold for the table in *quality_summary*; otherwise WARNING.

        Parameters
        ----------
        quality_summary:
            Dict produced by ``DataQualityChecker.score_dataframe``.  Must
            contain ``overall_score`` (float) and optionally ``table`` (str).

        Raises
        ------
        RuntimeError
            When the resolved severity is CRITICAL.
        """
        overall_score: float = quality_summary.get("overall_score", 1.0)
        table: str = quality_summary.get(
            "source", quality_summary.get("table", "unknown")
        )
        threshold = QUALITY_THRESHOLDS.get(table, 0.95)

        resolved_severity = "CRITICAL" if overall_score < threshold else "WARNING"

        for alert in self._alerts:
            # Upgrade individual alert severity if the overall result is CRITICAL
            effective_severity = (
                "CRITICAL" if resolved_severity == "CRITICAL" else alert.severity
            )
            log.warning(
                "[%s] table=%s rule=%s affected_rows=%d detected_at=%s "
                "sample_values=%s",
                effective_severity,
                alert.table,
                alert.rule,
                alert.affected_rows,
                alert.detected_at,
                alert.sample_values[:5],
            )

        if not self._alerts:
            log.info(
                "AlertManager.flush: no alerts for table=%s (score=%.4f)",
                table,
                overall_score,
            )

        if resolved_severity == "CRITICAL":
            summary_msg = (
                f"Data quality CRITICAL for table='{table}': "
                f"score={overall_score:.4f} < threshold={threshold:.4f}. "
                f"total_rows={quality_summary.get('total_rows', '?')}, "
                f"failed_rows={quality_summary.get('failed_rows', '?')}."
            )
            log.error(summary_msg)
            raise RuntimeError(summary_msg)

        self._alerts.clear()

    def to_dict(self) -> list[dict[str, Any]]:
        """Return all alerts as a list of plain dicts (for lineage serialisation)."""
        return [
            {
                "table": a.table,
                "rule": a.rule,
                "affected_rows": a.affected_rows,
                "sample_values": a.sample_values,
                "severity": a.severity,
                "detected_at": a.detected_at,
            }
            for a in self._alerts
        ]
