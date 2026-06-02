"""
API tests for the Inventory ingestion endpoint.

Stubs — QA owner: flesh out assertions, edge-cases, and error paths.
Endpoint base: /api/ingestion/inventory/
"""

import pytest
import requests


class TestInventoryIngestion:
    def test_list_inventory_authenticated(self, base_url, auth_headers):
        """GET /api/ingestion/inventory/ returns 200 and a paginated list."""
        resp = requests.get(
            f"{base_url}/api/ingestion/inventory/", headers=auth_headers
        )
        assert resp.status_code == 200
        # TODO: assert resp.json() has expected pagination shape

    def test_list_inventory_unauthenticated(self, base_url):
        """GET /api/ingestion/inventory/ without a token returns 401."""
        resp = requests.get(f"{base_url}/api/ingestion/inventory/")
        assert resp.status_code == 401

    def test_create_inventory_record(self, base_url, auth_headers, ingestion_job_id):
        """POST /api/ingestion/inventory/ creates a staging record and returns 201."""
        payload = {
            "job": ingestion_job_id,
            "product_id": "PROD-001",
            "warehouse_id": "WH-01",
            "quantity": 150,
        }
        resp = requests.post(
            f"{base_url}/api/ingestion/inventory/", headers=auth_headers, json=payload
        )
        assert resp.status_code == 201
        # TODO: assert returned fields match payload

    def test_create_inventory_missing_job(self, base_url, auth_headers):
        """POST without required `job` field returns 400."""
        resp = requests.post(
            f"{base_url}/api/ingestion/inventory/",
            headers=auth_headers,
            json={"product_id": "PROD-002", "quantity": 50},
        )
        assert resp.status_code == 400

    def test_get_inventory_by_id(self, base_url, auth_headers, ingestion_job_id):
        """Create a record, then GET it by ID."""
        create_resp = requests.post(
            f"{base_url}/api/ingestion/inventory/",
            headers=auth_headers,
            json={
                "job": ingestion_job_id,
                "product_id": "PROD-003",
                "warehouse_id": "WH-02",
                "quantity": 75,
            },
        )
        assert create_resp.status_code == 201
        record_id = create_resp.json()["id"]

        resp = requests.get(
            f"{base_url}/api/ingestion/inventory/{record_id}/", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == record_id

    def test_negative_quantity_rejected(self, base_url, auth_headers, ingestion_job_id):
        """Reject negative quantities. TODO: wire validator to serializer."""
        # TODO: implement quantity >= 0 validation in InventoryStagingRecordSerializer
        pass


@pytest.fixture(scope="module")
def ingestion_job_id(base_url, auth_headers):
    """Create an INVENTORY IngestionJob and return its ID."""
    resp = requests.post(
        f"{base_url}/api/ingestion/jobs/",
        headers=auth_headers,
        json={"source_type": "INVENTORY"},
    )
    assert resp.status_code == 201, f"Failed to create ingestion job: {resp.text}"
    return resp.json()["id"]
