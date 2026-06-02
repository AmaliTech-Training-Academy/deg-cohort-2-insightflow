"""
API tests for the POS (Point-of-Sale) ingestion endpoint.

Stubs — QA owner: flesh out assertions, edge-cases, and error paths.
Endpoint base: /api/ingestion/pos/
"""

import pytest
import requests


class TestPOSIngestion:
    def test_list_pos_records_authenticated(self, base_url, auth_headers):
        """GET /api/ingestion/pos/ returns 200 and a paginated list."""
        resp = requests.get(f"{base_url}/api/ingestion/pos/", headers=auth_headers)
        assert resp.status_code == 200
        # TODO: assert resp.json() has expected pagination shape

    def test_list_pos_records_unauthenticated(self, base_url):
        """GET /api/ingestion/pos/ without a token returns 401."""
        resp = requests.get(f"{base_url}/api/ingestion/pos/")
        assert resp.status_code == 401

    def test_create_pos_record(self, base_url, auth_headers, ingestion_job_id):
        """POST /api/ingestion/pos/ creates a staging record and returns 201."""
        payload = {
            "job": ingestion_job_id,
            "transaction_id": "TXN-001",
            "store_id": "STORE-01",
            "product_id": "PROD-001",
            "quantity": 2,
            "amount": "19.99",
        }
        resp = requests.post(
            f"{base_url}/api/ingestion/pos/", headers=auth_headers, json=payload
        )
        assert resp.status_code == 201
        # TODO: assert returned fields match payload

    def test_create_pos_record_missing_job(self, base_url, auth_headers):
        """POST without required `job` field returns 400."""
        resp = requests.post(
            f"{base_url}/api/ingestion/pos/",
            headers=auth_headers,
            json={"transaction_id": "TXN-002"},
        )
        assert resp.status_code == 400

    def test_get_pos_record_by_id(self, base_url, auth_headers, ingestion_job_id):
        """Create a record, then GET it by ID."""
        create_resp = requests.post(
            f"{base_url}/api/ingestion/pos/",
            headers=auth_headers,
            json={"job": ingestion_job_id, "transaction_id": "TXN-003", "quantity": 1},
        )
        assert create_resp.status_code == 201
        record_id = create_resp.json()["id"]

        resp = requests.get(
            f"{base_url}/api/ingestion/pos/{record_id}/", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == record_id


@pytest.fixture(scope="module")
def ingestion_job_id(base_url, auth_headers):
    """Create a POS IngestionJob and return its ID for use in POS tests."""
    resp = requests.post(
        f"{base_url}/api/ingestion/jobs/",
        headers=auth_headers,
        json={"source_type": "POS"},
    )
    assert resp.status_code == 201, f"Failed to create ingestion job: {resp.text}"
    return resp.json()["id"]
