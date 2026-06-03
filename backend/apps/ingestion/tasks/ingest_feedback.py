import logging

from celery import shared_task

from ..services.feedback_ingestion_service import FeedbackIngestionService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def ingest_feedback(self) -> dict:
    """
    Fetches all feedback records from the external API and ingests them.

    Retries up to 3 times with exponential backoff (60s, 120s, 240s) on failure.
    """
    logger.info("Starting feedback ingestion run")
    try:
        service = FeedbackIngestionService()
        return service.ingest()
    except Exception as exc:
        logger.error(f"Feedback ingestion failed — retrying. Error: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
