import logging

from celery import shared_task
from django.db import OperationalError

from ..models.base import InjectionJob
from ..services.csv_services import POSIngestionService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_pos_file(self, job_id: int) -> None:
    """
    Picks up the saved CSV file and processes it.
    All logic lives in POSIngestionService.process_job().

    bind=True        — gives us access to self (the task instance)
    max_retries=3    — retries up to 3 times if something crashes
    """
    logger.info(f"Starting POS processing — job_id={job_id}")

    try:
        job = InjectionJob.objects.get(id=job_id)
    except InjectionJob.DoesNotExist:
        # job was deleted before task ran — nothing to do
        logger.warning(f"Job {job_id} not found — skipping")
        return
    except OperationalError as exc:
        # DB unreachable before we even loaded the job — retry
        logger.error(f"Job {job_id} — DB unavailable on load, retrying. Error: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))

    try:
        service = POSIngestionService()
        service.process_job(job)

    except Exception as exc:
        # Check if process_job already marked it FAILED (business logic failure —
        # bad data, FK mismatches). Guard the refresh with its own try-except so a
        # DB outage here doesn't swallow the exception and kill retry logic silently.
        try:
            job.refresh_from_db()
            if job.status == InjectionJob.StatusChoices.FAILED:
                logger.error(f"Job {job_id} marked FAILED by service — not retrying")
                return
        except OperationalError:
            pass  # DB is down — fall through to infrastructure retry below

        # Infrastructure failure (DB down, Redis timeout, etc.) — retry with backoff
        logger.error(
            f"Job {job_id} hit infrastructure error — retrying "
            f"(attempt {self.request.retries + 1}/3). Error: {exc}"
        )
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
