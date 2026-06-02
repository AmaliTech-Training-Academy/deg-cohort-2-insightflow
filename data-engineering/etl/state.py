"""Incremental-load watermark detection for the InsightFlow ETL pipeline.

Instead of maintaining a separate state table, the watermark is derived
directly from the data already in the warehouse:

  • For sales / feedback: MAX(fullDate) across all fact tables joined to dimDate
  • For inventory: same dimDate reference

This is self-healing — if a run fails partway through, the next run
automatically re-processes from the last complete date, with no stale state.

Triggering: any scheduler (e.g. Metabase refresh webhook, cron, or manual
run) calls etl_pipeline.py without --since; the watermark is auto-detected
from the warehouse and only new records are extracted.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.engine import Engine

log = logging.getLogger("insightflow.state")


def get_watermark_date(warehouse_engine: Engine) -> date | None:
    """Return the most recent date already loaded into the warehouse.

    Queries the maximum ``fullDate`` referenced by any fact table via dimDate.
    Returns ``None`` when the warehouse is empty, which triggers a full load.

    Parameters
    ----------
    warehouse_engine:
        SQLAlchemy engine connected to the warehouse DB.
    """
    query = text("""
        SELECT MAX(d."fullDate")
        FROM "dimDate" d
        WHERE EXISTS (
            SELECT 1 FROM "factSales"             fs WHERE fs."dateKey" = d."dateKey"
        ) OR EXISTS (
            SELECT 1 FROM "factFeedback"           ff WHERE ff."dateKey" = d."dateKey"
        ) OR EXISTS (
            SELECT 1 FROM "factInventorySnapshot"  fi WHERE fi."dateKey" = d."dateKey"
        )
    """)

    with warehouse_engine.connect() as conn:
        try:
            result = conn.execute(query).scalar()
        except Exception:
            log.warning("Could not query warehouse for watermark — assuming empty")
            return None

    if result is None:
        log.info("Warehouse is empty — full load will be performed")
        return None

    watermark: date = result if isinstance(result, date) else result.date()
    log.info("Warehouse watermark: %s — incremental load from this date", watermark)
    return watermark
