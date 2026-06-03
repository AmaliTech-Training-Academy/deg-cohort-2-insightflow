"""
Unit tests for POS ingestion service.

Tests POSIngestionService validate_upload(), accept_upload(), and process_job() methods.
"""

import io
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from apps.ingestion.services.csv_services import POSIngestionService


class TestPOSIngestionServiceValidateUpload:
    """Test POSIngestionService.validate_upload()."""

    @pytest.fixture
    def service(self):
        return POSIngestionService()

    def test_file_size_exceeds_limit(self, service):
        """Files over 50MB rejected."""
        file = Mock()
        file.size = 51 * 1024 * 1024
        file.name = 'test.csv'

        result = service.validate_upload(file)

        assert result['ok'] is False
        assert 'maximum is 50MB' in result['error']

    def test_file_size_at_limit_accepted(self, service):
        """Files at 50MB limit accepted (if valid otherwise)."""
        file_content = b'transaction_id,date,store_id,cashier_id,product_sku,quantity,unit_price,discount_applied,total\n'
        file = io.BytesIO(file_content)
        file.name = 'test.csv'
        file.size = 50 * 1024 * 1024

        # Mock pandas
        with patch('apps.ingestion.services.csv_services.pd.read_csv') as mock_read:
            mock_read.return_value = Mock(columns=Mock(tolist=lambda: [
                'transaction_id', 'date', 'store_id', 'cashier_id',
                'product_sku', 'quantity', 'unit_price', 'discount_applied', 'total'
            ]))

            result = service.validate_upload(file)

            assert result['ok'] is True

    def test_non_csv_file_rejected(self, service):
        """Non-.csv files rejected."""
        file = Mock()
        file.size = 1024
        file.name = 'test.txt'

        result = service.validate_upload(file)

        assert result['ok'] is False
        assert 'Only .csv files' in result['error']

    def test_csv_extension_case_insensitive(self, service):
        """File extension check is case-insensitive."""
        file_content = b'transaction_id,date,store_id,cashier_id,product_sku,quantity,unit_price,discount_applied,total\n'
        file = io.BytesIO(file_content)
        file.name = 'test.CSV'
        file.size = 1024

        with patch('apps.ingestion.services.csv_services.pd.read_csv') as mock_read:
            mock_read.return_value = Mock(columns=Mock(tolist=lambda: [
                'transaction_id', 'date', 'store_id', 'cashier_id',
                'product_sku', 'quantity', 'unit_price', 'discount_applied', 'total'
            ]))

            result = service.validate_upload(file)

            assert result['ok'] is True

    def test_csv_parse_error(self, service):
        """Unparseable CSV rejected."""
        file = Mock()
        file.size = 1024
        file.name = 'test.csv'

        with patch('apps.ingestion.services.csv_services.pd.read_csv') as mock_read:
            mock_read.side_effect = Exception('Parse error')

            result = service.validate_upload(file)

            assert result['ok'] is False
            assert 'Could not read CSV' in result['error']

    def test_missing_required_columns(self, service):
        """Missing required columns reported."""
        file = Mock()
        file.size = 1024
        file.name = 'test.csv'

        with patch('apps.ingestion.services.csv_services.pd.read_csv') as mock_read:
            mock_read.return_value = Mock(columns=Mock(tolist=lambda: [
                'transaction_id', 'date', 'store_id'
                # Missing: cashier_id, product_sku, quantity, unit_price, discount_applied, total
            ]))

            result = service.validate_upload(file)

            assert result['ok'] is False
            assert 'missing_columns' in result
            assert len(result['missing_columns']) > 0

    def test_file_seek_reset_after_validation(self, service):
        """File pointer reset after validation."""
        file = Mock()
        file.size = 1024
        file.name = 'test.csv'

        with patch('apps.ingestion.services.csv_services.pd.read_csv') as mock_read:
            mock_read.return_value = Mock(columns=Mock(tolist=lambda: [
                'transaction_id', 'date', 'store_id', 'cashier_id',
                'product_sku', 'quantity', 'unit_price', 'discount_applied', 'total'
            ]))

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
        file_content = 'transaction_id,date,store_id,cashier_id,product_sku,quantity,unit_price,discount_applied,total\n'
        file_content += 'txn1,2024-06-01,5,101,SKU001,10,25.99,0.00,259.90\n'
        file_content += 'txn2,2024-06-01,5,101,SKU002,5,10.00,0.00,50.00\n'
        file = io.BytesIO(file_content.encode())

        count = service._count_rows(file)

        assert count == 2

    def test_count_rows_empty_file(self, service):
        """Empty file returns 0."""
        file = io.BytesIO(b'')

        count = service._count_rows(file)

        assert count == 0

    def test_count_rows_header_only(self, service):
        """Header-only file returns 0."""
        file_content = 'transaction_id,date,store_id,cashier_id,product_sku,quantity,unit_price,discount_applied,total\n'
        file = io.BytesIO(file_content.encode())

        count = service._count_rows(file)

        assert count == 0

    def test_file_seek_reset_after_count(self, service):
        """File pointer reset after counting."""
        file_content = 'col1,col2\nval1,val2\n'
        file = io.BytesIO(file_content.encode())

        service._count_rows(file)

        # File should be seeked back to 0
        assert file.tell() == 0
