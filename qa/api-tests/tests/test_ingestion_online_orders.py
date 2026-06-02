"""
API tests for the Online Orders ingestion endpoint.

Stubs — QA owner: flesh out assertions, edge-cases, and error paths.
Endpoint base: /api/ingestion/online-orders/
"""

import pytest
import requests


class TestOnlineOrdersIngestion:
    def test_list_online_orders_authenticated(self, base_url, auth_headers):
        """GET /api/ingestion/online-orders/ returns 200 and a paginated list."""
        resp = requests.get(
            f"{base_url}/api/ingestion/online-orders/", headers=auth_headers
        )
        assert resp.status_code == 200
        # TODO: assert resp.json() has expected pagination shape

    def test_list_online_orders_unauthenticated(self, base_url):
        """GET /api/ingestion/online-orders/ without a token returns 401."""
        resp = requests.get(f"{base_url}/api/ingestion/online-orders/")
        assert resp.status_code == 401

    def test_create_online_order_record(self, base_url, auth_headers, ingestion_job_id):
        """Create online order record via POST and return 201."""
        payload = {
            "job": ingestion_job_id,
            "order_id": "ORD-001",
            "customer_id": "CUST-01",
            "amount": "49.95",
            "items": [{"sku": "SKU-1", "qty": 1}],
        }
        resp = requests.post(
            f"{base_url}/api/ingestion/online-orders/",
            headers=auth_headers,
            json=payload,
        )
        assert resp.status_code == 201
        # TODO: assert returned fields match payload

    def test_create_online_order_missing_job(self, base_url, auth_headers):
        """POST without required `job` field returns 400."""
        resp = requests.post(
            f"{base_url}/api/ingestion/online-orders/",
            headers=auth_headers,
            json={"order_id": "ORD-002"},
        )
        assert resp.status_code == 400

    def test_get_online_order_by_id(self, base_url, auth_headers, ingestion_job_id):
        """Create a record, then GET it by ID."""
        create_resp = requests.post(
            f"{base_url}/api/ingestion/online-orders/",
            headers=auth_headers,
            json={"job": ingestion_job_id, "order_id": "ORD-003"},
        )
        assert create_resp.status_code == 201
        record_id = create_resp.json()["id"]

        resp = requests.get(
            f"{base_url}/api/ingestion/online-orders/{record_id}/",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == record_id


@pytest.fixture(scope="module")
def ingestion_job_id(base_url, auth_headers):
    """Create an ONLINE_ORDERS IngestionJob and return its ID."""
    resp = requests.post(
        f"{base_url}/api/ingestion/jobs/",
        headers=auth_headers,
        json={"source_type": "ONLINE_ORDERS"},
    )
    assert resp.status_code == 201, f"Failed to create ingestion job: {resp.text}"
    return resp.json()["id"]
