"""
API tests for the POS (Point-of-Sale) ingestion endpoint.

Tests CSV file upload, validation, and processing workflows.
Endpoint base: /api/ingestion/pos/
"""

import io
# import pytest
import requests


class TestPOSIngestionUpload:
    """Test POS CSV file upload endpoint."""

    def test_upload_valid_csv_returns_202(self, base_url, auth_headers):
        """POST valid CSV to /api/ingestion/pos/ returns 202 Accepted."""
        csv_content = (
            'transaction_id,date,store_id,cashier_id,product_sku,quantity,'
            'unit_price,discount_applied,total\n'
            'TXN001,2024-06-01,5,101,SKU001,10,25.99,0.00,259.90\n'
        )
        files = {'file': ('test.csv', io.BytesIO(csv_content.encode()), 'text/csv')}

        resp = requests.post(
            f"{base_url}/api/ingestion/pos/",
            headers=auth_headers,
            files=files
        )

        assert resp.status_code == 202
        data = resp.json()
        assert 'job_id' in data
        assert 'status' in data
        assert data['status'] == 'pending'
        assert 'total_rows' in data
        assert data['total_rows'] == 1

    def test_upload_without_auth_returns_401(self, base_url):
        """POST without authentication returns 401."""
        csv_content = (
            'transaction_id,date,store_id,cashier_id,product_sku,quantity,'
            'unit_price,discount_applied,total\n'
            'TXN001,2024-06-01,5,101,SKU001,10,25.99,0.00,259.90\n'
        )
        files = {'file': ('test.csv', io.BytesIO(csv_content.encode()), 'text/csv')}

        resp = requests.post(f"{base_url}/api/ingestion/pos/", files=files)

        assert resp.status_code == 401

    def test_upload_non_csv_file_returns_400(self, base_url, auth_headers):
        """Uploading non-CSV file returns 400."""
        files = {'file': ('test.txt', io.BytesIO(b'not csv'), 'text/plain')}

        resp = requests.post(
            f"{base_url}/api/ingestion/pos/",
            headers=auth_headers,
            files=files
        )

        assert resp.status_code == 400
        assert 'error' in resp.json()

    def test_upload_missing_required_columns_returns_400(self, base_url, auth_headers):
        """CSV missing required columns returns 400."""
        csv_content = 'transaction_id,date,store_id\nTXN001,2024-06-01,5\n'
        files = {'file': ('test.csv', io.BytesIO(csv_content.encode()), 'text/csv')}

        resp = requests.post(
            f"{base_url}/api/ingestion/pos/",
            headers=auth_headers,
            files=files
        )

        assert resp.status_code == 400
        assert 'missing_columns' in resp.json()

    def test_upload_response_contains_poll_message(self, base_url, auth_headers):
        """Successful upload includes polling endpoint in response."""
        csv_content = (
            'transaction_id,date,store_id,cashier_id,product_sku,quantity,'
            'unit_price,discount_applied,total\n'
            'TXN001,2024-06-01,5,101,SKU001,10,25.99,0.00,259.90\n'
        )
        files = {'file': ('test.csv', io.BytesIO(csv_content.encode()), 'text/csv')}

        resp = requests.post(
            f"{base_url}/api/ingestion/pos/",
            headers=auth_headers,
            files=files
        )

        assert resp.status_code == 202
        data = resp.json()
        assert 'message' in data
        assert 'Poll GET' in data['message']

    def test_upload_multiple_rows_counted(self, base_url, auth_headers):
        """CSV with multiple rows returns correct total_rows count."""
        csv_content = (
            'transaction_id,date,store_id,cashier_id,product_sku,quantity,'
            'unit_price,discount_applied,total\n'
            'TXN001,2024-06-01,5,101,SKU001,10,25.99,0.00,259.90\n'
            'TXN002,2024-06-01,5,102,SKU002,5,15.00,0.00,75.00\n'
            'TXN003,2024-06-01,5,103,SKU003,20,8.50,1.00,169.00\n'
        )
        files = {'file': ('test.csv', io.BytesIO(csv_content.encode()), 'text/csv')}

        resp = requests.post(
            f"{base_url}/api/ingestion/pos/",
            headers=auth_headers,
            files=files
        )

        assert resp.status_code == 202
        assert resp.json()['total_rows'] == 3


class TestPOSIngestionList:
    """Test GET /api/ingestion/pos/ — list endpoint."""

    def test_list_pos_records_authenticated(self, base_url, auth_headers):
        """GET /api/ingestion/pos/ returns 200 with paginated list."""
        resp = requests.get(f"{base_url}/api/ingestion/pos/", headers=auth_headers)
        assert resp.status_code == 200

    def test_list_pos_records_unauthenticated(self, base_url):
        """GET /api/ingestion/pos/ without a token returns 401."""
        resp = requests.get(f"{base_url}/api/ingestion/pos/")
        assert resp.status_code == 401


class TestPOSIngestionDetail:
    """Test GET/PUT/DELETE /api/ingestion/pos/{id}/ — detail endpoints."""

    def test_get_nonexistent_record_returns_404(self, base_url, auth_headers):
        """GET /api/ingestion/pos/{invalid_id}/ returns 404."""
        resp = requests.get(
            f"{base_url}/api/ingestion/pos/999999/",
            headers=auth_headers
        )

        assert resp.status_code == 404

