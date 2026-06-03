import logging

from celery import shared_task

from ..models.base import IngestionJob
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
    logger.info(f'Starting POS processing — job_id={job_id}')

    try:
        job = IngestionJob.objects.get(id=job_id)

    except IngestionJob.DoesNotExist:
        # job was deleted before task ran — nothing to do
        logger.warning(f'Job {job_id} not found — skipping')
        return

    try:
        service = POSIngestionService()
        service.process_job(job)

    except Exception as exc:
        logger.error(f'Job {job_id} failed — retrying. Error: {exc}')

        # exponential backoff: 60s, 120s, 240s
        raise self.retry(
            exc=exc,
            countdown=60 * (2 ** self.request.retries)
        )