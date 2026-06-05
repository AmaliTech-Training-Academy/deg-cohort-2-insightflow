"""
DB-backed tests for OnlineInjectionJob model, ingestion service, and Celery task.
"""

from unittest.mock import patch

import pytest
from apps.ingestion.connectors.online_orders import OnlineOrdersAPIError
from apps.ingestion.models.online_injection_job import OnlineInjectionJob
from apps.ingestion.services.online_orders_service import OnlineOrdersIngestionService

VALID_ORDER: dict = {
    "onlineOrderId": 1,
    "customerId": "CUST-000001",
    "orderDatetime": "2026-05-20T16:10:32.002120",
    "shippingProvince": "Northern",
    "orderStatus": "shipped",
    "paymentMethod": "paypal",
    "lines": [
        {
            "lineId": 1,
            "onlineOrderId": 1,
            "productSKU": "PROD-0000028",
            "quantity": 2,
            "unitPrice": "913.04",
            "discountApplied": "29.80",
            "totalAmount": "1796.28",
        }
    ],
}


@pytest.mark.django_db
class TestOnlineInjectionJobModel:
    def test_create_job_defaults(self):
        job = OnlineInjectionJob.objects.create()
        assert job.status == OnlineInjectionJob.StatusChoices.PENDING
        assert job.trigger == OnlineInjectionJob.TriggerChoices.SCHEDULED
        assert job.valid_orders == 0
        assert job.error_orders == 0
        assert job.pages_fetched == 0

    def test_model_db_table(self):
        assert OnlineInjectionJob._meta.db_table == "online_injection_job"

    def test_str_representation(self):
        job = OnlineInjectionJob.objects.create()
        assert str(job.id) in str(job)
        assert "pending" in str(job)


@pytest.mark.django_db
class TestOnlineOrdersIngestionService:
    @pytest.fixture
    def service(self):
        return OnlineOrdersIngestionService()

    def test_create_job_returns_pending(self, service):
        job = service.create_job()
        assert job.status == OnlineInjectionJob.StatusChoices.PENDING
        assert job.id is not None

    def test_create_job_manual_trigger(self, service):
        job = service.create_job(trigger="manual")
        assert job.trigger == OnlineInjectionJob.TriggerChoices.MANUAL

    def test_process_job_completes_on_success(self, service):
        with patch(
            "apps.ingestion.services.online_orders_service.iter_all_pages"
        ) as mock_pages:
            mock_pages.return_value = iter([[VALID_ORDER]])
            job = service.create_job()
            service.process_job(job)
            job.refresh_from_db()
            assert job.status == OnlineInjectionJob.StatusChoices.COMPLETED
            assert job.pages_fetched == 1

    def test_process_job_marks_failed_on_api_error(self, service):
        with patch(
            "apps.ingestion.services.online_orders_service.iter_all_pages"
        ) as mock_pages:
            mock_pages.side_effect = OnlineOrdersAPIError("connection failed")
            job = service.create_job()
            with pytest.raises(OnlineOrdersAPIError):
                service.process_job(job)
            job.refresh_from_db()
            assert job.status == OnlineInjectionJob.StatusChoices.FAILED
            assert "fatal_error" in job.error_report

    def test_upsert_creates_customer_if_missing(self, service):
        from apps.ingestion.models.base import Customer

        with patch(
            "apps.ingestion.services.online_orders_service.iter_all_pages"
        ) as mock_pages:
            mock_pages.return_value = iter([[VALID_ORDER]])
            service.process_job(service.create_job())
        assert Customer.objects.filter(customerId="CUST-000001").exists()

    def test_upsert_creates_product_if_missing(self, service):
        from apps.ingestion.models.inventory import Product

        with patch(
            "apps.ingestion.services.online_orders_service.iter_all_pages"
        ) as mock_pages:
            mock_pages.return_value = iter([[VALID_ORDER]])
            service.process_job(service.create_job())
        assert Product.objects.filter(productSKU="PROD-0000028").exists()

    def test_upsert_updates_order_status(self, service):
        from apps.ingestion.models.online_orders import OnlineOrder

        with patch(
            "apps.ingestion.services.online_orders_service.iter_all_pages"
        ) as mock_pages:
            mock_pages.return_value = iter([[VALID_ORDER]])
            service.process_job(service.create_job())

        updated = {**VALID_ORDER, "orderStatus": "delivered"}
        with patch(
            "apps.ingestion.services.online_orders_service.iter_all_pages"
        ) as mock_pages:
            mock_pages.return_value = iter([[updated]])
            service.process_job(service.create_job())

        assert OnlineOrder.objects.get(onlineOrderId=1).orderStatus == "delivered"

    def test_upsert_skips_duplicate_line(self, service):
        from apps.ingestion.models.online_orders import OnlineOrderLine

        for _ in range(2):
            with patch(
                "apps.ingestion.services.online_orders_service.iter_all_pages"
            ) as mock_pages:
                mock_pages.return_value = iter([[VALID_ORDER]])
                service.process_job(service.create_job())

        assert OnlineOrderLine.objects.filter(lineId=1).count() == 1

    def test_future_order_datetime_is_skipped(self, service):
        from apps.ingestion.models.online_orders import OnlineOrder

        future_order = {**VALID_ORDER, "orderDatetime": "2099-01-01T00:00:00"}
        with patch(
            "apps.ingestion.services.online_orders_service.iter_all_pages"
        ) as mock_pages:
            mock_pages.return_value = iter([[future_order]])
            job = service.create_job()
            service.process_job(job)

        job.refresh_from_db()
        assert OnlineOrder.objects.filter(onlineOrderId=1).count() == 0
        assert job.error_orders == 1
        assert job.valid_orders == 0

    def test_future_hour_same_day_is_skipped(self, service):
        from datetime import datetime, timedelta

        from apps.ingestion.models.online_orders import OnlineOrder

        future_dt = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
        future_order = {**VALID_ORDER, "orderDatetime": future_dt}
        with patch(
            "apps.ingestion.services.online_orders_service.iter_all_pages"
        ) as mock_pages:
            mock_pages.return_value = iter([[future_order]])
            job = service.create_job()
            service.process_job(job)

        job.refresh_from_db()
        assert OnlineOrder.objects.filter(onlineOrderId=1).count() == 0
        assert job.error_orders == 1

    def test_future_order_error_report_contains_reason(self, service):
        future_order = {**VALID_ORDER, "orderDatetime": "2099-06-15T10:00:00"}
        with patch(
            "apps.ingestion.services.online_orders_service.iter_all_pages"
        ) as mock_pages:
            mock_pages.return_value = iter([[future_order]])
            job = service.create_job()
            service.process_job(job)

        job.refresh_from_db()
        assert "future" in str(job.error_report)

    def test_past_order_datetime_is_accepted(self, service):
        from apps.ingestion.models.online_orders import OnlineOrder

        with patch(
            "apps.ingestion.services.online_orders_service.iter_all_pages"
        ) as mock_pages:
            mock_pages.return_value = iter([[VALID_ORDER]])
            service.process_job(service.create_job())

        assert OnlineOrder.objects.filter(onlineOrderId=1).exists()


@pytest.mark.django_db
class TestFetchOnlineOrdersTask:
    def test_task_skips_missing_job(self):
        from apps.ingestion.tasks.fetch_online_orders import fetch_online_orders

        fetch_online_orders.apply(args=[99999]).get()

    def test_task_calls_process_job(self):
        from apps.ingestion.tasks.fetch_online_orders import fetch_online_orders

        job = OnlineInjectionJob.objects.create()
        with patch(
            "apps.ingestion.tasks.fetch_online_orders.OnlineOrdersIngestionService"
        ) as MockService:
            mock_instance = MockService.return_value
            fetch_online_orders.apply(args=[job.id]).get()
            mock_instance.process_job.assert_called_once_with(job)
