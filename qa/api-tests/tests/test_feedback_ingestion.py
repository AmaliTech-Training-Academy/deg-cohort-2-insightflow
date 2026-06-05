"""
Tests for feedback survey ingestion — service, task, and trigger view.
"""

from unittest.mock import MagicMock, patch

import pytest
from apps.ingestion.models.base import Customer
from apps.ingestion.models.feedback import FeedbackSurvey
from apps.ingestion.models.feedback_ingestion_job import FeedbackIngestionJob
from apps.ingestion.models.online_orders import OnlineOrder
from apps.ingestion.services.feedback_ingestion_service import FeedbackIngestionService
from apps.ingestion.tasks.ingest_feedback import ingest_feedback
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


def _record(**overrides) -> dict:
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


@pytest.mark.django_db
class TestFeedbackIngestionService:
    @pytest.fixture(autouse=True)
    def setup(self):
        user = User.objects.create_user(username="testuser", password="pass")
        self.customer = Customer.objects.create(customerId="CUST-000001", userId=user)

    def _service(self, records):
        connector = MagicMock()
        connector.fetch_all.return_value = records
        return FeedbackIngestionService(connector=connector)

    def test_first_ingest_creates_record(self):
        summary = self._service([_record()]).ingest()
        assert FeedbackSurvey.objects.count() == 1
        assert summary["created"] == 1
        assert summary["skipped_duplicates"] == 0

    def test_second_ingest_skips_duplicate(self):
        svc = self._service([_record()])
        svc.ingest()
        summary = svc.ingest()
        assert FeedbackSurvey.objects.count() == 1
        assert summary["created"] == 0
        assert summary["skipped_duplicates"] == 1

    def test_different_response_ids_both_created(self):
        summary = self._service([_record(responseId=1), _record(responseId=2)]).ingest()
        assert FeedbackSurvey.objects.count() == 2
        assert summary["created"] == 2

    def test_future_submission_date_recorded_as_error(self):
        summary = self._service([_record(submissionDate="2099-01-01")]).ingest()
        assert FeedbackSurvey.objects.count() == 0
        assert summary["errors"] == 1
        assert "future" in summary["error_details"][0]["error"]

    def test_invalid_submission_date_recorded_as_error(self):
        summary = self._service([_record(submissionDate="not-a-date")]).ingest()
        assert FeedbackSurvey.objects.count() == 0
        assert summary["errors"] == 1
        assert "Invalid submissionDate" in summary["error_details"][0]["error"]

    def test_today_submission_date_is_accepted(self):
        from datetime import date

        summary = self._service(
            [_record(submissionDate=date.today().isoformat())]
        ).ingest()
        assert FeedbackSurvey.objects.count() == 1
        assert summary["errors"] == 0

    def test_missing_customer_recorded_as_error(self):
        summary = self._service([_record(customerId="CUST-UNKNOWN")]).ingest()
        assert FeedbackSurvey.objects.count() == 0
        assert summary["errors"] == 1
        assert "CUST-UNKNOWN" in summary["error_details"][0]["error"]

    def test_missing_online_order_does_not_block_ingestion(self):
        summary = self._service([_record(onlineOrderId=9999)]).ingest()
        assert FeedbackSurvey.objects.count() == 1
        assert FeedbackSurvey.objects.get(responseId=1).onlineOrderId is None
        assert summary["errors"] == 0

    def test_existing_online_order_resolved(self):
        order = OnlineOrder.objects.create(
            onlineOrderId=42,
            customerId=self.customer,
            orderDatetime=timezone.now(),
            shippingProvince="Accra",
            orderStatus="delivered",
            paymentMethod="card",
        )
        self._service([_record(onlineOrderId=42)]).ingest()
        assert FeedbackSurvey.objects.get(responseId=1).onlineOrderId == order

    def test_summary_totals_correct(self):
        user2 = User.objects.create_user(username="testuser2", password="pass")
        Customer.objects.create(customerId="CUST-000002", userId=user2)
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
        records = [
            _record(responseId=1),
            _record(responseId=2, customerId="CUST-000002"),
            _record(responseId=3, customerId="CUST-MISSING"),
        ]
        summary = self._service(records).ingest()
        assert summary["total_fetched"] == 3
        assert summary["created"] == 1
        assert summary["skipped_duplicates"] == 1
        assert summary["errors"] == 1

    def test_summary_is_logged(self):
        with patch(
            "apps.ingestion.services.feedback_ingestion_service.logger"
        ) as mock_log:
            self._service([_record()]).ingest()
        mock_log.info.assert_called_once()
        assert "Feedback ingestion complete" in mock_log.info.call_args[0][0]

    def test_bulk_ingest_creates_all_records(self):
        users = [
            User.objects.create_user(username=f"bulk{i}", password="pass")
            for i in range(5)
        ]
        for i, u in enumerate(users):
            Customer.objects.create(customerId=f"BULK-{i:06d}", userId=u)

        records = [
            _record(responseId=100 + i, customerId=f"BULK-{i:06d}") for i in range(5)
        ]
        summary = self._service(records).ingest()
        assert FeedbackSurvey.objects.count() == 5
        assert summary["created"] == 5
        assert summary["errors"] == 0


@pytest.mark.django_db
class TestIngestFeedbackTask:
    def test_task_max_retries(self):
        assert ingest_feedback.max_retries == 3

    def test_task_calls_service(self):
        job = FeedbackIngestionJob.objects.create()
        with patch(
            "apps.ingestion.tasks.ingest_feedback.FeedbackIngestionService"
        ) as MockSvc:
            MockSvc.return_value.ingest.return_value = {
                "total_fetched": 0,
                "created": 0,
                "skipped_duplicates": 0,
                "errors": 0,
                "error_details": [],
            }
            ingest_feedback.apply(args=[job.id]).get()
            MockSvc.return_value.ingest.assert_called_once()

    def test_task_marks_job_completed(self):
        job = FeedbackIngestionJob.objects.create()
        with patch(
            "apps.ingestion.tasks.ingest_feedback.FeedbackIngestionService"
        ) as MockSvc:
            MockSvc.return_value.ingest.return_value = {
                "total_fetched": 5,
                "created": 3,
                "skipped_duplicates": 2,
                "errors": 0,
                "error_details": [],
            }
            ingest_feedback.apply(args=[job.id]).get()
        job.refresh_from_db()
        assert job.status == FeedbackIngestionJob.StatusChoices.COMPLETED
        assert job.total_fetched == 5
        assert job.created_count == 3

    def test_task_marks_job_failed_on_connector_error(self):
        job = FeedbackIngestionJob.objects.create()
        with patch(
            "apps.ingestion.tasks.ingest_feedback.FeedbackIngestionService"
        ) as MockSvc:
            MockSvc.return_value.ingest.side_effect = ConnectionError("API unreachable")
            with pytest.raises(Exception):
                ingest_feedback.apply(args=[job.id], throw=True).get()
        job.refresh_from_db()
        assert job.status == FeedbackIngestionJob.StatusChoices.FAILED

    def test_task_handles_missing_job_gracefully(self):
        result = ingest_feedback.apply(args=[99999]).get()
        assert result == {}
