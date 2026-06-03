"""
Unit tests for POS views.

Tests POSStagingListCreateView (GET list + POST CSV upload) and
POSStagingDetailView (GET / PATCH / DELETE) using APIRequestFactory so
no live server or URL routing is required.
"""

import io
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.ingestion.models.inventory import Category, Product, Store
from apps.ingestion.models.pos import Cashier, PosTransaction, PosTransactionLine
from apps.ingestion.views.pos import POSStagingDetailView, POSStagingListCreateView

User = get_user_model()


# ── helpers ───────────────────────────────────────────────────────────────────

def _csv_file(rows=1):
    """Return an in-memory CSV file with `rows` data rows."""
    header = (
        "transaction_id,date,store_id,cashier_id,"
        "product_sku,quantity,unit_price,discount_applied,total\n"
    )
    body = "".join(
        f"TXN{i:03d},2024-06-01,1,1,PROD-0000001,2,25.00,0.00,50.00\n"
        for i in range(1, rows + 1)
    )
    content = (header + body).encode()
    f = io.BytesIO(content)
    f.name = "test.csv"
    return f


def _mock_job(job_id=1, total_rows=1):
    job = MagicMock()
    job.id = job_id
    job.status = "pending"
    job.total_rows = total_rows
    return job


# ── list / create view ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPOSStagingListView:
    """Tests for GET /api/ingestion/pos/."""

    def setup_method(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="tester", email="tester@test.com", password="pass"
        )
        self.view = POSStagingListCreateView.as_view()

    def test_authenticated_get_returns_200(self):
        """GET with a valid token returns 200."""
        request = self.factory.get("/api/ingestion/pos/")
        force_authenticate(request, user=self.user)
        response = self.view(request)
        assert response.status_code == 200

    def test_unauthenticated_get_returns_401(self):
        """GET without authentication returns 401."""
        request = self.factory.get("/api/ingestion/pos/")
        response = self.view(request)
        assert response.status_code == 401

    def test_get_returns_paginated_structure(self):
        """GET returns paginated wrapper with count and results keys."""
        request = self.factory.get("/api/ingestion/pos/")
        force_authenticate(request, user=self.user)
        response = self.view(request)
        assert "count" in response.data
        assert "results" in response.data

    def test_get_empty_results_when_no_records(self):
        """GET returns results=[] when no PosTransactionLine records exist."""
        request = self.factory.get("/api/ingestion/pos/")
        force_authenticate(request, user=self.user)
        response = self.view(request)
        assert response.data["results"] == []
        assert response.data["count"] == 0


# ── CSV upload ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPOSStagingCSVUpload:
    """Tests for POST /api/ingestion/pos/ with a CSV file."""

    def setup_method(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="tester", email="tester@test.com", password="pass"
        )
        self.view = POSStagingListCreateView.as_view()

    def _post_csv(self, file, mock_validate_result=None, mock_job=None):
        """Helper: patch service + task, POST the file, return response."""
        if mock_validate_result is None:
            mock_validate_result = {"ok": True}
        if mock_job is None:
            mock_job = _mock_job()

        with patch("apps.ingestion.views.pos.service.validate_upload") as mv, \
             patch("apps.ingestion.views.pos.service.accept_upload") as ma, \
             patch("apps.ingestion.views.pos.process_pos_file") as mt:

            mv.return_value = mock_validate_result
            ma.return_value = mock_job
            mt.delay.return_value = None

            request = self.factory.post(
                "/api/ingestion/pos/", {"file": file}, format="multipart"
            )
            force_authenticate(request, user=self.user)
            response = self.view(request)

        return response, mt

    def test_valid_csv_returns_202(self):
        """Valid CSV upload returns HTTP 202 Accepted."""
        response, _ = self._post_csv(_csv_file())
        assert response.status_code == 202

    def test_response_contains_job_id(self):
        """202 response contains job_id."""
        job = _mock_job(job_id=5)
        response, _ = self._post_csv(_csv_file(), mock_job=job)
        assert response.data["job_id"] == 5

    def test_response_contains_status(self):
        """202 response contains status field."""
        response, _ = self._post_csv(_csv_file())
        assert "status" in response.data
        assert response.data["status"] == "pending"

    def test_response_contains_total_rows(self):
        """202 response contains total_rows matching the uploaded file."""
        job = _mock_job(total_rows=3)
        response, _ = self._post_csv(_csv_file(rows=3), mock_job=job)
        assert response.data["total_rows"] == 3

    def test_response_contains_poll_message(self):
        """202 response includes a message with a poll URL hint."""
        response, _ = self._post_csv(_csv_file())
        assert "message" in response.data
        assert "Poll GET" in response.data["message"]

    def test_celery_task_dispatched_with_job_id(self):
        """Celery task is called with the correct job id."""
        job = _mock_job(job_id=99)
        _, mock_task = self._post_csv(_csv_file(), mock_job=job)
        mock_task.delay.assert_called_once_with(99)

    def test_validation_failure_returns_400(self):
        """If service.validate_upload fails, returns 400 with error key."""
        response, _ = self._post_csv(
            _csv_file(),
            mock_validate_result={
                "ok": False,
                "error": "Missing required columns",
                "missing_columns": ["cashier_id"],
            },
        )
        assert response.status_code == 400
        assert "error" in response.data

    def test_validation_failure_missing_columns_in_response(self):
        """400 response from column mismatch includes missing_columns key."""
        response, _ = self._post_csv(
            _csv_file(),
            mock_validate_result={
                "ok": False,
                "error": "Missing required columns",
                "missing_columns": ["cashier_id", "product_sku"],
            },
        )
        assert "missing_columns" in response.data

    def test_validation_ok_key_not_in_400_response(self):
        """The internal 'ok' key is stripped from 400 error responses."""
        response, _ = self._post_csv(
            _csv_file(),
            mock_validate_result={"ok": False, "error": "File too large"},
        )
        assert "ok" not in response.data

    def test_unauthenticated_upload_returns_401(self):
        """POST without authentication returns 401 — no service calls made."""
        request = self.factory.post(
            "/api/ingestion/pos/", {"file": _csv_file()}, format="multipart"
        )
        response = self.view(request)
        assert response.status_code == 401

    def test_celery_not_called_when_validation_fails(self):
        """Celery task must NOT be dispatched when validation fails."""
        with patch("apps.ingestion.views.pos.service.validate_upload") as mv, \
             patch("apps.ingestion.views.pos.process_pos_file") as mt:

            mv.return_value = {"ok": False, "error": "Bad file"}
            mt.delay.return_value = None

            request = self.factory.post(
                "/api/ingestion/pos/", {"file": _csv_file()}, format="multipart"
            )
            force_authenticate(request, user=self.user)
            self.view(request)

        mt.delay.assert_not_called()


# ── detail view ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPOSStagingDetailView:
    """Tests for GET / PATCH / DELETE /api/ingestion/pos/<pk>/."""

    def setup_method(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="tester", email="tester@test.com", password="pass"
        )
        self.view = POSStagingDetailView.as_view()

        # Build a full PosTransactionLine fixture
        store = Store.objects.create(storeId=1, storeName="Test Store", province="Ontario")
        cashier = Cashier.objects.create(
            cashierId=1, storeId=store, fullName="Test Cashier", userId=self.user
        )
        transaction = PosTransaction.objects.create(
            posTransactionId=1,
            storeId=store,
            cashierId=cashier,
            transactionDatetime=timezone.now(),
        )
        category = Category.objects.create(categoryId=1, name="Electronics")
        product = Product.objects.create(
            productSKU="PROD-0000001", productName="Laptop", categoryId=category
        )
        self.line = PosTransactionLine.objects.create(
            lineId=1,
            posTransactionId=transaction,
            productSKU=product,
            quantity=2,
            unitPrice=Decimal("99.99"),
            discountApplied=Decimal("0.00"),
            totalAmount=Decimal("199.98"),
        )

    def test_get_existing_record_returns_200(self):
        """GET /pos/<pk>/ with a valid pk returns 200."""
        request = self.factory.get(f"/api/ingestion/pos/{self.line.lineId}/")
        force_authenticate(request, user=self.user)
        response = self.view(request, pk=self.line.lineId)
        assert response.status_code == 200

    def test_get_returns_correct_lineId(self):
        """GET response contains the correct lineId."""
        request = self.factory.get(f"/api/ingestion/pos/{self.line.lineId}/")
        force_authenticate(request, user=self.user)
        response = self.view(request, pk=self.line.lineId)
        assert response.data["lineId"] == self.line.lineId

    def test_get_returns_correct_quantity(self):
        """GET response contains the correct quantity value."""
        request = self.factory.get(f"/api/ingestion/pos/{self.line.lineId}/")
        force_authenticate(request, user=self.user)
        response = self.view(request, pk=self.line.lineId)
        assert response.data["quantity"] == 2

    def test_get_nonexistent_returns_404(self):
        """GET /pos/999999/ returns 404."""
        request = self.factory.get("/api/ingestion/pos/999999/")
        force_authenticate(request, user=self.user)
        response = self.view(request, pk=999999)
        assert response.status_code == 404

    def test_get_unauthenticated_returns_401(self):
        """GET without auth returns 401."""
        request = self.factory.get(f"/api/ingestion/pos/{self.line.lineId}/")
        response = self.view(request, pk=self.line.lineId)
        assert response.status_code == 401

    def test_delete_returns_204(self):
        """DELETE /pos/<pk>/ returns 204 No Content."""
        request = self.factory.delete(f"/api/ingestion/pos/{self.line.lineId}/")
        force_authenticate(request, user=self.user)
        response = self.view(request, pk=self.line.lineId)
        assert response.status_code == 204

    def test_delete_removes_record_from_db(self):
        """DELETE actually removes the record from the database."""
        request = self.factory.delete(f"/api/ingestion/pos/{self.line.lineId}/")
        force_authenticate(request, user=self.user)
        self.view(request, pk=self.line.lineId)
        assert not PosTransactionLine.objects.filter(lineId=self.line.lineId).exists()

    def test_patch_updates_quantity(self):
        """PATCH /pos/<pk>/ updates a single field."""
        request = self.factory.patch(
            f"/api/ingestion/pos/{self.line.lineId}/",
            {"quantity": 10},
            format="json",
        )
        force_authenticate(request, user=self.user)
        response = self.view(request, pk=self.line.lineId)
        assert response.status_code == 200
        self.line.refresh_from_db()
        assert self.line.quantity == 10
