"""
Tests for feedback survey ingestion.

Covers:
- Deduplication by responseId
- Retry behaviour on connector failure
- Ingestion summary output
"""
import logging
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.authentication.models import User
from apps.ingestion.models.base import Customer
from apps.ingestion.models.feedback import FeedbackSurvey
from apps.ingestion.models.online_orders import OnlineOrder
from apps.ingestion.services.feedback_ingestion_service import FeedbackIngestionService
from apps.ingestion.tasks.ingest_feedback import ingest_feedback


def _make_record(**overrides) -> dict:
    base = {
        "responseId": 1,
        "customerId": "CUST-000001",
        "onlineOrderId": None,
        "submissionDate": "2025-10-01",
        "satisfactionScore": 4,
        "npsScore": 7,
        "productRating": 4,
        "deliveryRating": 3,
        "freeTextComments": "Great service.",
    }
    base.update(overrides)
    return base


class FeedbackIngestionDeduplicationTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="testuser", password="pass")
        self.customer = Customer.objects.create(customerId="CUST-000001", userId=user)

    def test_first_ingest_creates_record(self):
        connector = MagicMock()
        connector.fetch_all.return_value = [_make_record()]
        service = FeedbackIngestionService(connector=connector)

        summary = service.ingest()

        self.assertEqual(FeedbackSurvey.objects.count(), 1)
        self.assertEqual(summary["created"], 1)
        self.assertEqual(summary["skipped_duplicates"], 0)

    def test_second_ingest_skips_duplicate(self):
        connector = MagicMock()
        connector.fetch_all.return_value = [_make_record()]
        service = FeedbackIngestionService(connector=connector)

        service.ingest()
        summary = service.ingest()  # second run with same data

        self.assertEqual(FeedbackSurvey.objects.count(), 1)
        self.assertEqual(summary["created"], 0)
        self.assertEqual(summary["skipped_duplicates"], 1)

    def test_different_response_ids_are_both_created(self):
        connector = MagicMock()
        connector.fetch_all.return_value = [
            _make_record(responseId=1),
            _make_record(responseId=2),
        ]
        service = FeedbackIngestionService(connector=connector)

        summary = service.ingest()

        self.assertEqual(FeedbackSurvey.objects.count(), 2)
        self.assertEqual(summary["created"], 2)

    def test_missing_customer_is_recorded_as_error_not_exception(self):
        connector = MagicMock()
        connector.fetch_all.return_value = [_make_record(customerId="CUST-UNKNOWN")]
        service = FeedbackIngestionService(connector=connector)

        summary = service.ingest()

        self.assertEqual(FeedbackSurvey.objects.count(), 0)
        self.assertEqual(summary["errors"], 1)
        self.assertIn("CUST-UNKNOWN", summary["error_details"][0]["error"])

    def test_missing_online_order_does_not_prevent_ingestion(self):
        connector = MagicMock()
        connector.fetch_all.return_value = [_make_record(onlineOrderId=9999)]
        service = FeedbackIngestionService(connector=connector)

        summary = service.ingest()

        self.assertEqual(FeedbackSurvey.objects.count(), 1)
        record = FeedbackSurvey.objects.get(responseId=1)
        self.assertIsNone(record.onlineOrderId)
        self.assertEqual(summary["created"], 1)
        self.assertEqual(summary["errors"], 0)

    def test_online_order_fk_resolved_when_it_exists(self):
        user = User.objects.get(username="testuser")
        order = OnlineOrder.objects.create(
            onlineOrderId=42,
            customerId=self.customer,
            orderDatetime="2025-09-01T12:00:00Z",
            shippingProvince="Accra",
            orderStatus="delivered",
            paymentMethod="card",
        )
        connector = MagicMock()
        connector.fetch_all.return_value = [_make_record(onlineOrderId=42)]
        service = FeedbackIngestionService(connector=connector)

        service.ingest()

        record = FeedbackSurvey.objects.get(responseId=1)
        self.assertEqual(record.onlineOrderId, order)


class FeedbackIngestionSummaryTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="testuser2", password="pass")
        self.customer = Customer.objects.create(customerId="CUST-000001", userId=user)

    def test_summary_totals_are_correct(self):
        connector = MagicMock()
        connector.fetch_all.return_value = [
            _make_record(responseId=1),
            _make_record(responseId=2),
            _make_record(responseId=3, customerId="CUST-MISSING"),  # error
        ]
        service = FeedbackIngestionService(connector=connector)

        # pre-seed one so it becomes a duplicate
        FeedbackSurvey.objects.create(
            responseId=1,
            customerId=self.customer,
            submissionDate="2025-10-01",
            satisfactionScore=4,
            npsScore=7,
            productRating=4,
            deliveryRating=3,
            freeTextComments="",
        )

        summary = service.ingest()

        self.assertEqual(summary["total_fetched"], 3)
        self.assertEqual(summary["created"], 1)        # responseId=2 is new
        self.assertEqual(summary["skipped_duplicates"], 1)  # responseId=1 exists
        self.assertEqual(summary["errors"], 1)         # CUST-MISSING

    def test_summary_is_logged(self):
        connector = MagicMock()
        connector.fetch_all.return_value = [_make_record()]
        service = FeedbackIngestionService(connector=connector)

        with self.assertLogs("apps.ingestion.services.feedback_ingestion_service", level=logging.INFO) as log_ctx:
            service.ingest()

        self.assertTrue(any("Feedback ingestion complete" in line for line in log_ctx.output))


class FeedbackIngestionRetryTest(TestCase):
    def test_task_is_configured_for_three_retries(self):
        self.assertEqual(ingest_feedback.max_retries, 3)

    def test_task_raises_on_connector_failure(self):
        with patch(
            "apps.ingestion.tasks.ingest_feedback.FeedbackIngestionService"
        ) as MockService:
            instance = MockService.return_value
            instance.ingest.side_effect = ConnectionError("API unreachable")

            with self.assertRaises(Exception):
                ingest_feedback.apply(throw=True)

            instance.ingest.assert_called_once()

    def test_task_calls_retry_on_failure(self):
        """Verify the task delegates to self.retry() rather than swallowing the error."""
        with patch(
            "apps.ingestion.tasks.ingest_feedback.FeedbackIngestionService"
        ) as MockService:
            instance = MockService.return_value
            exc = ConnectionError("API unreachable")
            instance.ingest.side_effect = exc

            # Patch the task's retry method so we can assert it is called
            with patch.object(ingest_feedback, "retry", side_effect=exc) as mock_retry:
                with self.assertRaises(ConnectionError):
                    ingest_feedback.apply(throw=True)

                mock_retry.assert_called_once()

    def test_task_succeeds_without_retry_when_no_error(self):
        with patch(
            "apps.ingestion.tasks.ingest_feedback.FeedbackIngestionService"
        ) as MockService:
            instance = MockService.return_value
            instance.ingest.return_value = {
                "total_fetched": 5,
                "created": 5,
                "skipped_duplicates": 0,
                "errors": 0,
                "error_details": [],
            }

            result = ingest_feedback.apply().get()

            self.assertEqual(result["created"], 5)
            instance.ingest.assert_called_once()
