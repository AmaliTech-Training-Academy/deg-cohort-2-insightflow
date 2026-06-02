"""
API tests for the Customer Feedback ingestion endpoint.

Stubs — QA owner: flesh out assertions, edge-cases, and error paths.
Endpoint base: /api/ingestion/feedback/
"""

import pytest
import requests


class TestFeedbackIngestion:
    def test_list_feedback_authenticated(self, base_url, auth_headers):
        """GET /api/ingestion/feedback/ returns 200 and a paginated list."""
        resp = requests.get(f"{base_url}/api/ingestion/feedback/", headers=auth_headers)
        assert resp.status_code == 200
        # TODO: assert resp.json() has expected pagination shape

    def test_list_feedback_unauthenticated(self, base_url):
        """GET /api/ingestion/feedback/ without a token returns 401."""
        resp = requests.get(f"{base_url}/api/ingestion/feedback/")
        assert resp.status_code == 401

    def test_create_feedback_record(self, base_url, auth_headers, ingestion_job_id):
        """POST /api/ingestion/feedback/ creates a staging record and returns 201."""
        payload = {
            "job": ingestion_job_id,
            "feedback_id": "FB-001",
            "customer_id": "CUST-01",
            "rating": 4,
            "comment": "Great service!",
        }
        resp = requests.post(
            f"{base_url}/api/ingestion/feedback/", headers=auth_headers, json=payload
        )
        assert resp.status_code == 201
        # TODO: assert returned fields match payload

    def test_create_feedback_missing_job(self, base_url, auth_headers):
        """POST without required `job` field returns 400."""
        resp = requests.post(
            f"{base_url}/api/ingestion/feedback/",
            headers=auth_headers,
            json={"feedback_id": "FB-002", "rating": 3},
        )
        assert resp.status_code == 400

    def test_get_feedback_by_id(self, base_url, auth_headers, ingestion_job_id):
        """Create a record, then GET it by ID."""
        create_resp = requests.post(
            f"{base_url}/api/ingestion/feedback/",
            headers=auth_headers,
            json={"job": ingestion_job_id, "feedback_id": "FB-003", "rating": 5},
        )
        assert create_resp.status_code == 201
        record_id = create_resp.json()["id"]

        resp = requests.get(
            f"{base_url}/api/ingestion/feedback/{record_id}/", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == record_id

    def test_rating_out_of_range(self, base_url, auth_headers, ingestion_job_id):
        """Ratings outside 1-5 rejected. TODO: wire validator to serializer."""
        # TODO: implement rating range validation in FeedbackStagingRecordSerializer
        pass


@pytest.fixture(scope="module")
def ingestion_job_id(base_url, auth_headers):
    """Create a FEEDBACK IngestionJob and return its ID."""
    resp = requests.post(
        f"{base_url}/api/ingestion/jobs/",
        headers=auth_headers,
        json={"source_type": "FEEDBACK"},
    )
    assert resp.status_code == 201, f"Failed to create ingestion job: {resp.text}"
    return resp.json()["id"]
