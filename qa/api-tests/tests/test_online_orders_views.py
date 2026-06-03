"""
Live API tests for online orders ingestion endpoints.
Requires a running backend server (skipped automatically if not reachable).
"""

import requests


class TestOnlineOrdersTriggerView:
    def test_trigger_returns_202(self, base_url, auth_headers):
        resp = requests.post(
            f"{base_url}/api/ingestion/online-orders/trigger/",
            headers=auth_headers,
            timeout=5,
        )
        assert resp.status_code == 202

    def test_trigger_unauthenticated_returns_401(self, base_url):
        resp = requests.post(
            f"{base_url}/api/ingestion/online-orders/trigger/",
            timeout=5,
        )
        assert resp.status_code == 401

    def test_trigger_response_has_job_id(self, base_url, auth_headers):
        resp = requests.post(
            f"{base_url}/api/ingestion/online-orders/trigger/",
            headers=auth_headers,
            timeout=5,
        )
        assert "id" in resp.json()


class TestOnlineOrdersJobStatusView:
    def test_status_returns_200_for_known_job(self, base_url, auth_headers):
        job_id = requests.post(
            f"{base_url}/api/ingestion/online-orders/trigger/",
            headers=auth_headers,
            timeout=5,
        ).json()["id"]
        resp = requests.get(
            f"{base_url}/api/ingestion/online-orders/{job_id}/status/",
            headers=auth_headers,
            timeout=5,
        )
        assert resp.status_code == 200

    def test_status_returns_404_for_unknown_job(self, base_url, auth_headers):
        resp = requests.get(
            f"{base_url}/api/ingestion/online-orders/999999/status/",
            headers=auth_headers,
            timeout=5,
        )
        assert resp.status_code == 404


class TestOnlineOrdersJobListView:
    def test_jobs_list_returns_200(self, base_url, auth_headers):
        resp = requests.get(
            f"{base_url}/api/ingestion/online-orders/jobs/",
            headers=auth_headers,
            timeout=5,
        )
        assert resp.status_code == 200

    def test_jobs_list_unauthenticated_returns_401(self, base_url):
        resp = requests.get(
            f"{base_url}/api/ingestion/online-orders/jobs/",
            timeout=5,
        )
        assert resp.status_code == 401
