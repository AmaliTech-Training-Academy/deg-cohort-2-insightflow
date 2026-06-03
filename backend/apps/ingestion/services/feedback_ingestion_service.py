import logging

from ..connectors.feedback import FeedbackAPIConnector
from ..models.base import Customer
from ..models.feedback import FeedbackSurvey
from ..models.online_orders import OnlineOrder

logger = logging.getLogger(__name__)


class FeedbackIngestionService:
    """
    Fetches feedback survey records from the external API and persists them.

    Deduplication: records are keyed by responseId — existing rows are skipped.
    Summary: total fetched / created / skipped / errors are logged after each run.
    """

    def __init__(self, connector=None):
        self._connector = connector or FeedbackAPIConnector()

    def ingest(self) -> dict:
        records = self._connector.fetch_all()
        total = len(records)
        created_count = 0
        skipped_count = 0
        error_details = []

        for record in records:
            try:
                was_created = self._ingest_one(record)
                if was_created:
                    created_count += 1
                else:
                    skipped_count += 1
            except Exception as exc:
                error_details.append(
                    {
                        "responseId": record.get("responseId"),
                        "error": str(exc),
                    }
                )

        summary = {
            "total_fetched": total,
            "created": created_count,
            "skipped_duplicates": skipped_count,
            "errors": len(error_details),
            "error_details": error_details,
        }
        logger.info("Feedback ingestion complete", extra={"ingestion_summary": summary})
        return summary

    # ── private ──────────────────────────────────────────────────────────────

    def _ingest_one(self, record: dict) -> bool:
        """
        Persists a single feedback record.
        Returns True if the record was newly created, False if it already existed.
        Raises ValueError if a required foreign key cannot be resolved.
        """
        customer_id = record.get("customerId")
        try:
            customer = Customer.objects.get(customerId=customer_id)
        except Customer.DoesNotExist:
            raise ValueError(
                f"Customer '{customer_id}' not found"
                f" — skipping response {record.get('responseId')}"
            )

        online_order_id = record.get("onlineOrderId")
        online_order = None
        if online_order_id is not None:
            try:
                online_order = OnlineOrder.objects.get(onlineOrderId=online_order_id)
            except OnlineOrder.DoesNotExist:
                pass  # nullable FK — tolerate missing orders

        _, created = FeedbackSurvey.objects.get_or_create(
            responseId=record["responseId"],
            defaults={
                "customerId": customer,
                "onlineOrderId": online_order,
                "submissionDate": record["submissionDate"],
                "satisfactionScore": record["satisfactionScore"],
                "npsScore": record["npsScore"],
                "productRating": record["productRating"],
                "deliveryRating": record["deliveryRating"],
                "freeTextComments": record.get("freeTextComments", ""),
            },
        )
        return bool(created)
