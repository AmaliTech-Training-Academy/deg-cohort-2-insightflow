"""Celery tasks for the InsightFlow ETL pipeline.

Single task: ``run_etl_task``

Wraps the existing ``run_pipeline()`` from ``etl_pipeline.py`` so it can be
dispatched asynchronously by the NOTIFY listener.  The task uses a Redis
distributed lock to prevent concurrent ETL runs — if a run is already in
progress when the task fires, the new invocation exits immediately rather than
queuing a duplicate load.

The underlying ``run_pipeline()`` uses the watermark from ``etl/state.py``, so
only records newer than the last successful load are extracted.  Running this
task multiple times is safe and idempotent.
"""

from __future__ import annotations

import logging
import os

import redis as redis_lib  # type: ignore[import-untyped]
from celery_app import app

log = logging.getLogger("insightflow.tasks")

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
_LOCK_KEY = "etl:run_lock"
_LOCK_TIMEOUT = 3600  # max seconds an ETL run should ever take


@app.task(
    name="etl.run_pipeline",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_etl_task(self) -> None:  # type: ignore[override]
    """Execute the incremental ETL pipeline as a Celery task.

    Triggered by the NOTIFY listener after data lands in the OLTP database.
    Acquires a Redis lock so only one ETL run executes at a time — any
    concurrent invocation exits cleanly without error.

    On failure the task retries up to 3 times with a 60-second backoff.
    """
    r = redis_lib.Redis.from_url(_REDIS_URL, ssl_cert_reqs=None)
    lock = r.lock(_LOCK_KEY, timeout=_LOCK_TIMEOUT, blocking_timeout=0)

    if not lock.acquire(blocking=False):
        log.info(
            "ETL already running — skipping duplicate invocation (task_id=%s)",
            self.request.id,
        )
        return

    log.info("ETL task acquired lock — starting pipeline (task_id=%s)", self.request.id)
    try:
        # Import here to keep module load fast; run_pipeline does the heavy work
        from etl_pipeline import run_pipeline  # type: ignore[import]

        run_pipeline()
        log.info("ETL task completed successfully (task_id=%s)", self.request.id)
    except Exception as exc:
        log.error(
            "ETL task failed (task_id=%s): %s — scheduling retry",
            self.request.id,
            exc,
        )
        raise self.retry(exc=exc)
    finally:
        try:
            lock.release()
        except redis_lib.exceptions.LockNotOwnedError:
            pass  # lock already expired; safe to ignore
