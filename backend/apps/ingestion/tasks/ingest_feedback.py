import logging

from celery import shared_task

from ..models.feedback_ingestion_job import FeedbackIngestionJob
from ..services.feedback_ingestion_service import FeedbackIngestionService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def ingest_feedback(self, job_id: int) -> dict:
    try:
        job = FeedbackIngestionJob.objects.get(pk=job_id)
    except FeedbackIngestionJob.DoesNotExist:
        logger.error("FeedbackIngestionJob %s not found — aborting", job_id)
        return {}

    job.status = FeedbackIngestionJob.StatusChoices.RUNNING
    job.save(update_fields=["status", "updated_at"])

    logger.info("Starting feedback ingestion run (job_id=%s)", job_id)
    try:
        summary = FeedbackIngestionService().ingest()
        job.status = FeedbackIngestionJob.StatusChoices.COMPLETED
        job.total_fetched = summary["total_fetched"]
        job.created_count = summary["created"]
        job.skipped_duplicates = summary["skipped_duplicates"]
        job.errors = summary["errors"]
        job.error_details = summary["error_details"]
        job.save()
        return summary
    except Exception as exc:
        logger.error("Feedback ingestion failed (job_id=%s): %s", job_id, exc)
        job.status = FeedbackIngestionJob.StatusChoices.FAILED
        job.error_details = [{"error": str(exc)}]
        job.save(update_fields=["status", "error_details", "updated_at"])
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
