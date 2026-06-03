"""PostgreSQL LISTEN/NOTIFY listener for event-driven ETL triggering.

How it works
────────────
1. A PostgreSQL trigger on each relevant OLTP table fires
   ``pg_notify('etl_trigger', <table_name>)`` after every INSERT/UPDATE batch.
2. This listener holds an open connection to the OLTP database and waits for
   those notifications using ``select.select()``.
3. When a notification arrives a **debounce window** starts in Redis:
   - Any pending ETL task is cancelled (revoked).
   - A fresh ``run_etl_task`` is scheduled with a ``countdown`` of
     ``DEBOUNCE_SECONDS`` (default 300 s / 5 min).
   - If another notification arrives before the window closes, the pending
     task is cancelled and a new window starts — so a burst of uploads
     produces exactly one ETL run once the writes settle.
4. The listener reconnects automatically if the database connection drops.

Entry point
───────────
Run directly:  ``python -m etl.listener``
Or via Docker: ``python -m etl.listener`` in the etl-listener service.

Environment variables
─────────────────────
DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD  — OLTP source DB
REDIS_URL                                             — Redis broker URL
ETL_DEBOUNCE_SECONDS                                  — debounce window (default 300)
"""

from __future__ import annotations

import logging
import os
import select
import time

import psycopg2
import psycopg2.extensions
import redis  # type: ignore[import-untyped]

log = logging.getLogger("insightflow.listener")

DEBOUNCE_SECONDS = int(os.getenv("ETL_DEBOUNCE_SECONDS", "300"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
_CHANNEL = "etl_trigger"
_PENDING_KEY = "etl:pending_task_id"
_RECONNECT_DELAY = 10  # seconds between reconnect attempts

_DSN = (
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'insightflow_app')} "
    f"user={os.getenv('DB_USER', 'postgres')} "
    f"password={os.getenv('DB_PASSWORD', 'postgres')}"
)


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------


def _redis() -> redis.Redis:  # type: ignore[type-arg]
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def _cancel_pending(r: redis.Redis) -> None:  # type: ignore[type-arg]
    """Revoke any queued ETL task that has not yet started."""
    task_id = r.get(_PENDING_KEY)
    if task_id:
        # Import app here to avoid circular dependency at module load
        from celery_app import app  # type: ignore[import]

        app.control.revoke(task_id, terminate=False)
        r.delete(_PENDING_KEY)
        log.debug("Cancelled pending ETL task %s", task_id)


def _schedule_etl(r: redis.Redis) -> None:  # type: ignore[type-arg]
    """Cancel the previous pending task and schedule a fresh ETL run.

    The task is delayed by ``DEBOUNCE_SECONDS``.  If another notification
    arrives before the delay expires, this function is called again, the
    previous task is revoked, and the countdown resets.
    """
    from etl.tasks import run_etl_task  # type: ignore[import]

    _cancel_pending(r)
    result = run_etl_task.apply_async(countdown=DEBOUNCE_SECONDS)

    # Store task ID with TTL slightly longer than the countdown so it
    # expires automatically if somehow the revoke never fires.
    r.set(_PENDING_KEY, result.id, ex=DEBOUNCE_SECONDS + 120)
    log.info(
        "ETL scheduled in %ds (task_id=%s)",
        DEBOUNCE_SECONDS,
        result.id,
    )


# ---------------------------------------------------------------------------
# PostgreSQL connection
# ---------------------------------------------------------------------------


def _connect() -> psycopg2.extensions.connection:
    """Open an OLTP connection, enable autocommit, and LISTEN on the channel."""
    conn = psycopg2.connect(_DSN)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    with conn.cursor() as cur:
        cur.execute(f"LISTEN {_CHANNEL};")
    log.info("Connected to OLTP DB and listening on channel '%s'", _CHANNEL)
    return conn


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run() -> None:
    """Start the listener loop.  Reconnects automatically on connection loss."""
    r = _redis()
    conn: psycopg2.extensions.connection | None = None

    while True:
        try:
            if conn is None or conn.closed:
                conn = _connect()

            # Block up to 30 s waiting for a notification; prevents busy-wait
            # and allows the loop to check conn health periodically.
            readable, _, _ = select.select([conn], [], [], 30)
            if readable:
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    log.info(
                        "NOTIFY received: channel=%s table=%s",
                        notify.channel,
                        notify.payload,
                    )
                    _schedule_etl(r)

        except psycopg2.OperationalError as exc:
            log.error(
                "OLTP DB connection lost: %s — reconnecting in %ds",
                exc,
                _RECONNECT_DELAY,
            )
            if conn is not None:
                try:
                    conn.close()
                except Exception:  # noqa: BLE001
                    pass
            conn = None
            time.sleep(_RECONNECT_DELAY)

        except Exception as exc:  # noqa: BLE001
            log.error("Listener error: %s — continuing in 5s", exc)
            time.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    run()
