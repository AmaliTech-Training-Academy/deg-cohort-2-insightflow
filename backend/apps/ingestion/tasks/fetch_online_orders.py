import logging

from celery import shared_task

from ..models.online_injection_job import OnlineInjectionJob
from ..services.online_orders_service import OnlineOrdersIngestionService

logger = logging.getLogger(__name__)


@shared_task
def schedule_online_orders_fetch() -> None:
    service = OnlineOrdersIngestionService()
    job = service.create_job(trigger="scheduled")
    fetch_online_orders.delay(job.id)
    logger.info("Scheduled online orders fetch dispatched — job_id=%s", job.id)


@shared_task(bind=True, max_retries=3)
def fetch_online_orders(self, job_id: int) -> None:  # type: ignore[misc]
    logger.info("Starting online orders ingestion — job_id=%s", job_id)

    try:
        job = OnlineInjectionJob.objects.get(id=job_id)
    except OnlineInjectionJob.DoesNotExist:
        logger.warning("OnlineInjectionJob %s not found — skipping", job_id)
        return

    try:
        service = OnlineOrdersIngestionService()
        service.process_job(job)
    except Exception as exc:
        logger.error("OnlineInjectionJob %s failed — retrying. Error: %s", job_id, exc)
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
