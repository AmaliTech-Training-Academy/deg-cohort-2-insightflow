"""
Unit tests for POS ingestion service.

Tests POSIngestionService validate_upload(), accept_upload(), and process_job() methods.
"""

import io
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest
from apps.core.exceptions import (
    CSVParseException,
    FileSizeLimitException,
    UnsupportedFileTypeException,
    ValidationException,
)
from apps.ingestion.models.base import InjectionJob
from apps.ingestion.services.csv_services import POSIngestionService


class TestPOSIngestionServiceValidateUpload:
    """Test POSIngestionService.validate_upload()."""

    @pytest.fixture
    def service(self):
        return POSIngestionService()

    def test_file_size_exceeds_limit(self, service):
        """Files over 50MB rejected with FileSizeLimitException."""
        file = Mock()
        file.size = 51 * 1024 * 1024
        file.name = "test.csv"

        with pytest.raises(FileSizeLimitException) as exc_info:
            service.validate_upload(file)

        assert "maximum is 50MB" in str(exc_info.value.detail)

    def test_file_size_at_limit_accepted(self, service):
        """Files at exactly 50MB accepted — validate_upload returns None."""
        file_content = (
            b"transaction_id,date,store_id,cashier_id,"
            b"product_sku,quantity,unit_price,discount_applied,total\n"
        )
        file = io.BytesIO(file_content)
        file.name = "test.csv"
        file.size = 50 * 1024 * 1024

        with patch("apps.ingestion.services.csv_services.pd.read_csv") as mock_read:
            mock_read.return_value = Mock(
                columns=Mock(
                    tolist=lambda: [
                        "transaction_id",
                        "date",
                        "store_id",
                        "cashier_id",
                        "product_sku",
                        "quantity",
                        "unit_price",
                        "discount_applied",
                        "total",
                    ]
                )
            )

            result = service.validate_upload(file)

            assert result is None

    def test_non_csv_file_rejected(self, service):
        """Non-.csv files rejected with UnsupportedFileTypeException."""
        file = Mock()
        file.size = 1024
        file.name = "test.txt"

        with pytest.raises(UnsupportedFileTypeException) as exc_info:
            service.validate_upload(file)

        assert "Only .csv files" in str(exc_info.value.detail)

    def test_csv_extension_case_insensitive(self, service):
        """File extension check is case-insensitive — validate_upload returns None."""
        file_content = (
            b"transaction_id,date,store_id,cashier_id,"
            b"product_sku,quantity,unit_price,discount_applied,total\n"
        )
        file = io.BytesIO(file_content)
        file.name = "test.CSV"
        file.size = 1024

        with patch("apps.ingestion.services.csv_services.pd.read_csv") as mock_read:
            mock_read.return_value = Mock(
                columns=Mock(
                    tolist=lambda: [
                        "transaction_id",
                        "date",
                        "store_id",
                        "cashier_id",
                        "product_sku",
                        "quantity",
                        "unit_price",
                        "discount_applied",
                        "total",
                    ]
                )
            )

            result = service.validate_upload(file)

            assert result is None

    def test_csv_parse_error(self, service):
        """Unparseable CSV rejected with CSVParseException."""
        file = Mock()
        file.size = 1024
        file.name = "test.csv"

        with patch("apps.ingestion.services.csv_services.pd.read_csv") as mock_read:
            mock_read.side_effect = pd.errors.ParserError("bad CSV")

            with pytest.raises(CSVParseException) as exc_info:
                service.validate_upload(file)

            assert "Could not read CSV" in str(exc_info.value.detail)

    def test_missing_required_columns(self, service):
        """Missing required columns reported via ValidationException."""
        file = Mock()
        file.size = 1024
        file.name = "test.csv"

        with patch("apps.ingestion.services.csv_services.pd.read_csv") as mock_read:
            mock_read.return_value = Mock(
                columns=Mock(
                    tolist=lambda: [
                        "transaction_id",
                        "date",
                        "store_id",
                        # Missing: cashier_id, product_sku, quantity,
                        # unit_price, discount_applied, total
                    ]
                )
            )

            with pytest.raises(ValidationException) as exc_info:
                service.validate_upload(file)

            exc = exc_info.value
            assert "missing_columns" in exc.details
            assert len(exc.details["missing_columns"]) > 0

    def test_file_seek_reset_after_validation(self, service):
        """File pointer reset after validation."""
        file = Mock()
        file.size = 1024
        file.name = "test.csv"

        with patch("apps.ingestion.services.csv_services.pd.read_csv") as mock_read:
            mock_read.return_value = Mock(
                columns=Mock(
                    tolist=lambda: [
                        "transaction_id",
                        "date",
                        "store_id",
                        "cashier_id",
                        "product_sku",
                        "quantity",
                        "unit_price",
                        "discount_applied",
                        "total",
                    ]
                )
            )

            service.validate_upload(file)

            # file.seek(0) should have been called
            file.seek.assert_called()


class TestPOSIngestionServiceCountRows:
    """Test POSIngestionService._count_rows()."""

    @pytest.fixture
    def service(self):
        return POSIngestionService()

    def test_count_rows_with_header(self, service):
        """Correctly counts rows excluding header."""
        file_content = (
            "transaction_id,date,store_id,cashier_id,"
            "product_sku,quantity,unit_price,discount_applied,total\n"
        )
        file_content += "txn1,2024-06-01,5,101,SKU001,10,25.99,0.00,259.90\n"
        file_content += "txn2,2024-06-01,5,101,SKU002,5,10.00,0.00,50.00\n"
        file = io.BytesIO(file_content.encode())

        count = service._count_rows(file)

        assert count == 2

    def test_count_rows_empty_file(self, service):
        """Empty file returns 0."""
        file = io.BytesIO(b"")

        count = service._count_rows(file)

        assert count == 0

    def test_count_rows_header_only(self, service):
        """Header-only file returns 0."""
        file_content = (
            "transaction_id,date,store_id,cashier_id,"
            "product_sku,quantity,unit_price,discount_applied,total\n"
        )
        file = io.BytesIO(file_content.encode())

        count = service._count_rows(file)

        assert count == 0

    def test_file_seek_reset_after_count(self, service):
        """File pointer reset after counting."""
        file_content = "col1,col2\nval1,val2\n"
        file = io.BytesIO(file_content.encode())

        service._count_rows(file)

        # File should be seeked back to 0
        assert file.tell() == 0


class TestPOSIngestionServiceAcceptUpload:
    """Test POSIngestionService.accept_upload() — InjectionJob creation."""

    @pytest.fixture
    def service(self):
        return POSIngestionService()

    def _make_file(self, rows=2):
        header = (
            "transaction_id,date,store_id,cashier_id,"
            "product_sku,quantity,unit_price,discount_applied,total\n"
        )
        body = "".join(
            f"TXN{i:03d},2024-06-01,1,1,PROD-0000001,2,25.00,0.00,50.00\n"
            for i in range(1, rows + 1)
        )
        f = io.BytesIO((header + body).encode())
        f.name = "test.csv"
        return f

    def test_accept_upload_returns_injection_job(self, service):
        """accept_upload returns the InjectionJob instance created."""
        f = self._make_file()
        mock_job = MagicMock()
        mock_job.id = 1

        with patch(
            "apps.ingestion.services.csv_services.InjectionJob.objects.create"
        ) as mock_create:
            mock_create.return_value = mock_job

            result = service.accept_upload(f)

            assert result is mock_job

    def test_accept_upload_calls_objects_create(self, service):
        """accept_upload calls InjectionJob.objects.create exactly once."""
        f = self._make_file()
        mock_job = MagicMock()

        with patch(
            "apps.ingestion.services.csv_services.InjectionJob.objects.create"
        ) as mock_create:
            mock_create.return_value = mock_job

            service.accept_upload(f)

            mock_create.assert_called_once()

    def test_accept_upload_sets_status_pending(self, service):
        """accept_upload creates the job with StatusChoices.PENDING."""
        f = self._make_file()
        mock_job = MagicMock()

        with patch(
            "apps.ingestion.services.csv_services.InjectionJob.objects.create"
        ) as mock_create:
            mock_create.return_value = mock_job

            service.accept_upload(f)

            kwargs = mock_create.call_args[1]
            assert kwargs["status"] == InjectionJob.StatusChoices.PENDING

    def test_accept_upload_sets_total_rows(self, service):
        """accept_upload passes the correct row count to objects.create."""
        f = self._make_file(rows=3)
        mock_job = MagicMock()

        with patch(
            "apps.ingestion.services.csv_services.InjectionJob.objects.create"
        ) as mock_create:
            mock_create.return_value = mock_job

            service.accept_upload(f)

            kwargs = mock_create.call_args[1]
            assert kwargs["total_rows"] == 3

    def test_accept_upload_zero_rows_file(self, service):
        """accept_upload with a header-only file sets total_rows=0."""
        header_only = io.BytesIO(b"col1,col2\n")
        header_only.name = "empty.csv"
        mock_job = MagicMock()

        with patch(
            "apps.ingestion.services.csv_services.InjectionJob.objects.create"
        ) as mock_create:
            mock_create.return_value = mock_job

            service.accept_upload(header_only)

            kwargs = mock_create.call_args[1]
            assert kwargs["total_rows"] == 0

    def test_accept_upload_assigns_file_to_job(self, service):
        """accept_upload assigns the file to the job and calls save."""
        f = self._make_file()
        mock_job = MagicMock()

        with patch(
            "apps.ingestion.services.csv_services.InjectionJob.objects.create"
        ) as mock_create:
            mock_create.return_value = mock_job

            service.accept_upload(f)

            assert mock_job.file == f
            mock_job.save.assert_called_once_with(update_fields=["file"])


# ── Helpers shared by process_job tests ──────────────────────────────────────

_VALID_CSV = (
    "transaction_id,store_id,cashier_id,date,product_sku,"
    "quantity,unit_price,discount_applied,total\n"
    "1,1,10,2025-07-25T17:32:26,PROD-0000001,2,10.00,0.00,20.00\n"
    "1,1,10,2025-07-25T17:32:26,PROD-0000002,3,5.00,0.00,15.00\n"
    "2,2,20,2025-08-01T10:00:00,PROD-0000003,1,50.00,5.00,45.00\n"
)

_INVALID_CSV = (
    "transaction_id,store_id,cashier_id,date,product_sku,"
    "quantity,unit_price,discount_applied,total\n"
    ",,,,,,,,\n"  # all empty — fails validation
)

_VALID_DF = pd.read_csv(io.StringIO(_VALID_CSV))
_INVALID_DF = pd.read_csv(io.StringIO(_INVALID_CSV))


def _make_process_job(
    csv_content=_VALID_CSV,
    store_ids=(1, 2),
    cashier_ids=(10, 20),
    product_skus=("PROD-0000001", "PROD-0000002", "PROD-0000003"),
):
    """Return a context-manager stack that patches all DB dependencies."""
    import pandas as pd

    df = pd.read_csv(io.StringIO(csv_content))
    return (
        patch("apps.ingestion.services.csv_services.pd.read_csv", return_value=df),
        patch(
            "apps.ingestion.services.csv_services.Store.objects.values_list",
            return_value=list(store_ids),
        ),
        patch(
            "apps.ingestion.services.csv_services.Cashier.objects.values_list",
            return_value=list(cashier_ids),
        ),
        patch(
            "apps.ingestion.services.csv_services.Product.objects.values_list",
            return_value=list(product_skus),
        ),
        patch(
            "apps.ingestion.services.csv_services.PosTransaction.objects.bulk_create"
        ),
        patch(
            "apps.ingestion.services.csv_services"
            ".PosTransactionLine.objects.bulk_create"
        ),
        patch("apps.ingestion.services.csv_services.db_transaction.atomic"),
    )


def _make_job():
    job = MagicMock()
    job.id = 1
    job.file.path = "/tmp/test.csv"
    return job


class TestPOSIngestionServiceProcessJob:
    """Test POSIngestionService.process_job() — bulk insert optimisation."""

    @pytest.fixture
    def service(self):
        return POSIngestionService()

    def test_valid_csv_marks_job_completed(self, service):
        """All-valid rows result in job status COMPLETED."""
        job = _make_job()

        with (
            patch("apps.ingestion.services.csv_services.pd.read_csv") as mock_csv,
            patch(
                "apps.ingestion.services.csv_services.Store.objects.values_list",
                return_value=[1, 2],
            ),
            patch(
                "apps.ingestion.services.csv_services.Cashier.objects.values_list",
                return_value=[10, 20],
            ),
            patch(
                "apps.ingestion.services.csv_services.Product.objects.values_list",
                return_value=["PROD-0000001", "PROD-0000002", "PROD-0000003"],
            ),
            patch(
                "apps.ingestion.services.csv_services.PosTransaction.objects.filter",
                return_value=MagicMock(values_list=MagicMock(return_value=[])),
            ),
            patch(
                "apps.ingestion.services.csv_services"
                ".PosTransaction.objects.bulk_create"
            ),
            patch(
                "apps.ingestion.services.csv_services"
                ".PosTransactionLine.objects.bulk_create"
            ),
            patch(
                "apps.ingestion.services.csv_services.db_transaction.atomic"
            ) as mock_atomic,
        ):

            mock_csv.return_value = _VALID_DF
            mock_atomic.return_value.__enter__ = Mock(return_value=None)
            mock_atomic.return_value.__exit__ = Mock(return_value=False)

            service.process_job(job)

        assert job.status == "completed"

    def test_bulk_create_called_once_for_transactions(self, service):
        """PosTransaction.bulk_create called exactly once regardless of row count."""
        job = _make_job()

        with (
            patch("apps.ingestion.services.csv_services.pd.read_csv") as mock_csv,
            patch(
                "apps.ingestion.services.csv_services.Store.objects.values_list",
                return_value=[1, 2],
            ),
            patch(
                "apps.ingestion.services.csv_services.Cashier.objects.values_list",
                return_value=[10, 20],
            ),
            patch(
                "apps.ingestion.services.csv_services.Product.objects.values_list",
                return_value=["PROD-0000001", "PROD-0000002", "PROD-0000003"],
            ),
            patch(
                "apps.ingestion.services.csv_services.PosTransaction.objects.filter",
                return_value=MagicMock(values_list=MagicMock(return_value=[])),
            ),
            patch(
                "apps.ingestion.services.csv_services"
                ".PosTransaction.objects.bulk_create"
            ) as mock_txn_bulk,
            patch(
                "apps.ingestion.services.csv_services"
                ".PosTransactionLine.objects.bulk_create"
            ),
            patch(
                "apps.ingestion.services.csv_services.db_transaction.atomic"
            ) as mock_atomic,
        ):

            mock_csv.return_value = _VALID_DF
            mock_atomic.return_value.__enter__ = Mock(return_value=None)
            mock_atomic.return_value.__exit__ = Mock(return_value=False)

            service.process_job(job)

        mock_txn_bulk.assert_called_once()

    def test_bulk_create_called_once_for_lines(self, service):
        """PosTransactionLine.bulk_create called exactly once for all lines."""
        job = _make_job()

        with (
            patch("apps.ingestion.services.csv_services.pd.read_csv") as mock_csv,
            patch(
                "apps.ingestion.services.csv_services.Store.objects.values_list",
                return_value=[1, 2],
            ),
            patch(
                "apps.ingestion.services.csv_services.Cashier.objects.values_list",
                return_value=[10, 20],
            ),
            patch(
                "apps.ingestion.services.csv_services.Product.objects.values_list",
                return_value=["PROD-0000001", "PROD-0000002", "PROD-0000003"],
            ),
            patch(
                "apps.ingestion.services.csv_services.PosTransaction.objects.filter",
                return_value=MagicMock(values_list=MagicMock(return_value=[])),
            ),
            patch(
                "apps.ingestion.services.csv_services"
                ".PosTransaction.objects.bulk_create"
            ),
            patch(
                "apps.ingestion.services.csv_services"
                ".PosTransactionLine.objects.bulk_create"
            ) as mock_line_bulk,
            patch(
                "apps.ingestion.services.csv_services.db_transaction.atomic"
            ) as mock_atomic,
        ):

            mock_csv.return_value = _VALID_DF
            mock_atomic.return_value.__enter__ = Mock(return_value=None)
            mock_atomic.return_value.__exit__ = Mock(return_value=False)

            service.process_job(job)

        mock_line_bulk.assert_called_once()

    def test_missing_cashier_skipped_with_error_row(self, service):
        """Transaction with unknown cashier_id is skipped and logged as error."""
        job = _make_job()

        with (
            patch("apps.ingestion.services.csv_services.pd.read_csv") as mock_csv,
            patch(
                "apps.ingestion.services.csv_services.Store.objects.values_list",
                return_value=[1, 2],
            ),
            patch(
                "apps.ingestion.services.csv_services.Cashier.objects.values_list",
                return_value=[],
            ),
            patch(
                "apps.ingestion.services.csv_services.Product.objects.values_list",
                return_value=["PROD-0000001", "PROD-0000002", "PROD-0000003"],
            ),
            patch(
                "apps.ingestion.services.csv_services"
                ".PosTransaction.objects.bulk_create"
            ) as mock_txn_bulk,
            patch(
                "apps.ingestion.services.csv_services"
                ".PosTransactionLine.objects.bulk_create"
            ),
            patch(
                "apps.ingestion.services.csv_services.db_transaction.atomic"
            ) as mock_atomic,
        ):

            mock_csv.return_value = _VALID_DF
            mock_atomic.return_value.__enter__ = Mock(return_value=None)
            mock_atomic.return_value.__exit__ = Mock(return_value=False)

            service.process_job(job)

        # No transactions inserted because all cashier IDs are unknown
        mock_txn_bulk.assert_not_called()
        assert job.rejected_rows > 0

    def test_missing_product_skipped_with_error_row(self, service):
        """Line item with unknown product_sku is skipped and logged as error."""
        job = _make_job()

        with (
            patch("apps.ingestion.services.csv_services.pd.read_csv") as mock_csv,
            patch(
                "apps.ingestion.services.csv_services.Store.objects.values_list",
                return_value=[1, 2],
            ),
            patch(
                "apps.ingestion.services.csv_services.Cashier.objects.values_list",
                return_value=[10, 20],
            ),
            patch(
                "apps.ingestion.services.csv_services.Product.objects.values_list",
                return_value=[],
            ),
            patch(
                "apps.ingestion.services.csv_services.PosTransaction.objects.filter",
                return_value=MagicMock(values_list=MagicMock(return_value=[])),
            ),
            patch(
                "apps.ingestion.services.csv_services"
                ".PosTransaction.objects.bulk_create"
            ),
            patch(
                "apps.ingestion.services.csv_services"
                ".PosTransactionLine.objects.bulk_create"
            ) as mock_line_bulk,
            patch(
                "apps.ingestion.services.csv_services.db_transaction.atomic"
            ) as mock_atomic,
        ):

            mock_csv.return_value = _VALID_DF
            mock_atomic.return_value.__enter__ = Mock(return_value=None)
            mock_atomic.return_value.__exit__ = Mock(return_value=False)

            service.process_job(job)

        # No lines inserted — all SKUs unknown
        mock_line_bulk.assert_not_called()

    def test_all_invalid_rows_marks_job_completed_with_errors(self, service):
        """CSV with all invalid rows completes with error_rows > 0."""
        job = _make_job()

        with (
            patch("apps.ingestion.services.csv_services.pd.read_csv") as mock_csv,
            patch(
                "apps.ingestion.services.csv_services.Store.objects.values_list",
                return_value=[1],
            ),
            patch(
                "apps.ingestion.services.csv_services.Cashier.objects.values_list",
                return_value=[10],
            ),
            patch(
                "apps.ingestion.services.csv_services.Product.objects.values_list",
                return_value=["PROD-0000001"],
            ),
            patch(
                "apps.ingestion.services.csv_services"
                ".PosTransaction.objects.bulk_create"
            ),
            patch(
                "apps.ingestion.services.csv_services"
                ".PosTransactionLine.objects.bulk_create"
            ),
            patch(
                "apps.ingestion.services.csv_services.db_transaction.atomic"
            ) as mock_atomic,
        ):

            mock_csv.return_value = _INVALID_DF
            mock_atomic.return_value.__enter__ = Mock(return_value=None)
            mock_atomic.return_value.__exit__ = Mock(return_value=False)

            service.process_job(job)

        assert job.status == "completed"
        assert job.valid_rows == 0


class TestPOSIngestionServiceParseDateField:
    """Test POSIngestionService._parse_date_field() static method."""

    def test_iso_datetime_with_microseconds(self):
        """Full ISO 8601 datetime with microseconds parsed correctly."""
        result = POSIngestionService._parse_date_field("2025-07-25T17:32:26.865133")
        assert result is not None
        assert result.year == 2025
        assert result.hour == 17

    def test_iso_datetime_without_microseconds(self):
        """ISO 8601 datetime without microseconds parsed correctly."""
        result = POSIngestionService._parse_date_field("2025-07-25T17:32:26")
        assert result is not None
        assert result.year == 2025

    def test_date_only_yyyy_mm_dd(self):
        """Date-only YYYY-MM-DD format parsed correctly."""
        result = POSIngestionService._parse_date_field("2024-06-01")
        assert result is not None
        assert result.year == 2024
        assert result.month == 6

    def test_date_only_dd_mm_yyyy(self):
        """Date-only DD/MM/YYYY format parsed correctly."""
        result = POSIngestionService._parse_date_field("01/06/2024")
        assert result is not None

    def test_invalid_date_returns_none(self):
        """Unparseable value returns None."""
        assert POSIngestionService._parse_date_field("not-a-date") is None

    def test_none_input_returns_none(self):
        """None input returns None."""
        assert POSIngestionService._parse_date_field(None) is None

    def test_empty_string_returns_none(self):
        """Empty string returns None."""
        assert POSIngestionService._parse_date_field("") is None
