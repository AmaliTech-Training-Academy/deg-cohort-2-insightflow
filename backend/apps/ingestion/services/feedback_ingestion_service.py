import logging
from datetime import date

from django.db import transaction as db_transaction

from ..connectors.feedback import FeedbackAPIConnector
from ..models.base import Customer
from ..models.feedback import FeedbackSurvey
from ..models.online_orders import OnlineOrder

logger = logging.getLogger(__name__)


class FeedbackIngestionService:
    def __init__(self, connector=None):
        self._connector = connector or FeedbackAPIConnector()

    def ingest(self) -> dict:
        records = self._connector.fetch_all()
        total = len(records)

        customer_ids = {str(r["customerId"]) for r in records if r.get("customerId")}
        order_ids = {
            r["onlineOrderId"] for r in records if r.get("onlineOrderId") is not None
        }
        response_ids = {
            r["responseId"] for r in records if r.get("responseId") is not None
        }

        customers = {
            c.customerId: c
            for c in Customer.objects.filter(customerId__in=customer_ids)
        }
        orders = {
            o.onlineOrderId: o
            for o in OnlineOrder.objects.filter(onlineOrderId__in=order_ids)
        }
        existing_ids = set(
            FeedbackSurvey.objects.filter(responseId__in=response_ids).values_list(
                "responseId", flat=True
            )
        )

        to_create: list[FeedbackSurvey] = []
        error_details: list[dict] = []

        today = date.today()
        for r in records:
            raw_date = r.get("submissionDate")
            try:
                submission_date = date.fromisoformat(str(raw_date))
            except (TypeError, ValueError):
                error_details.append(
                    {
                        "responseId": r.get("responseId"),
                        "error": f"Invalid submissionDate '{raw_date}'",
                    }
                )
                continue
            if submission_date > today:
                error_details.append(
                    {
                        "responseId": r.get("responseId"),
                        "error": f"submissionDate '{raw_date}' is in the future",
                    }
                )
                continue

            cust = customers.get(str(r.get("customerId", "")))
            if cust is None:
                error_details.append(
                    {
                        "responseId": r.get("responseId"),
                        "error": f"Customer '{r.get('customerId')}' not found",
                    }
                )
                continue
            to_create.append(
                FeedbackSurvey(
                    responseId=r["responseId"],
                    customerId=cust,
                    onlineOrderId=orders.get(r.get("onlineOrderId")),
                    submissionDate=r["submissionDate"],
                    satisfactionScore=r["satisfactionScore"],
                    npsScore=r["npsScore"],
                    productRating=r["productRating"],
                    deliveryRating=r["deliveryRating"],
                    freeTextComments=r.get("freeTextComments", ""),
                )
            )

        with db_transaction.atomic():
            FeedbackSurvey.objects.bulk_create(to_create, ignore_conflicts=True)

        created = sum(1 for r in to_create if r.responseId not in existing_ids)
        skipped = sum(1 for r in to_create if r.responseId in existing_ids)

        summary = {
            "total_fetched": total,
            "created": created,
            "skipped_duplicates": skipped,
            "errors": len(error_details),
            "error_details": error_details,
        }
        logger.info("Feedback ingestion complete", extra={"ingestion_summary": summary})
        return summary
