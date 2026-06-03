"""Celery application for the InsightFlow data-engineering pipeline.

This module is the single Celery app entry point for all data-engineering
tasks.  Both the ETL worker and the NOTIFY listener import from here.

Configuration is read from environment variables (loaded via .env / Docker).
The app uses Redis as both broker and result backend, on database index 1
(index 0 is reserved for the Django/backend Celery app).
"""

from __future__ import annotations

import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")

app = Celery(
    "insightflow_etl",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["etl.tasks"],
)

app.conf.update(
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Reliability: task is re-queued if the worker dies mid-run
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # ETL is heavy — process one at a time
    # Route all ETL tasks to a dedicated queue
    task_routes={
        "etl.run_pipeline": {"queue": "etl"},
    },
    # Results expire after 24 h — enough for observability, not forever
    result_expires=86400,
)
