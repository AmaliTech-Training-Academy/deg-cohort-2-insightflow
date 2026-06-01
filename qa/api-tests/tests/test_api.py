import pytest
import requests


class TestAuth:
    def test_register_new_user(self, base_url):
        resp = requests.post(
            f"{base_url}/api/auth/register",
            json={
                "email": "testuser_qa@example.com",
                "first_name": "QA",
                "last_name": "Tester",
                "password": "password123",
            },
        )
        assert resp.status_code in (201, 400), f"Unexpected status: {resp.text}"
        if resp.status_code == 201:
            data = resp.json()
            assert "token" in data
            assert data["user"]["email"] == "testuser_qa@example.com"

    def test_login_valid_credentials(self, base_url):
        resp = requests.post(
            f"{base_url}/api/auth/login",
            json={"email": "admin@amalitech.com", "password": "password123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["email"] == "admin@amalitech.com"

    def test_login_invalid_credentials(self, base_url):
        resp = requests.post(
            f"{base_url}/api/auth/login",
            json={"email": "admin@amalitech.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 400

    def test_login_missing_fields(self, base_url):
        resp = requests.post(
            f"{base_url}/api/auth/login", json={"email": "admin@amalitech.com"}
        )
        assert resp.status_code == 400


class TestDataSources:
    def test_get_all_datasources(self, base_url, auth_headers):
        resp = requests.get(f"{base_url}/api/datasources/", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_datasource(self, base_url, auth_headers):
        resp = requests.post(
            f"{base_url}/api/datasources/",
            headers=auth_headers,
            json={
                "name": "QA Test Source",
                "type": "CSV",
                "file_path": "/tmp/qa_test.csv",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "QA Test Source"
        assert data["type"] == "CSV"
        return data["id"]

    def test_get_datasource_by_id(self, base_url, auth_headers):
        create_resp = requests.post(
            f"{base_url}/api/datasources/",
            headers=auth_headers,
            json={"name": "Fetch By ID Source", "type": "JSON"},
        )
        assert create_resp.status_code == 201
        ds_id = create_resp.json()["id"]

        resp = requests.get(
            f"{base_url}/api/datasources/{ds_id}/", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == ds_id

    def test_create_datasource_missing_fields(self, base_url, auth_headers):
        resp = requests.post(
            f"{base_url}/api/datasources/",
            headers=auth_headers,
            json={"name": "Missing Type"},
        )
        assert resp.status_code == 400

    def test_get_datasources_unauthenticated(self, base_url):
        resp = requests.get(f"{base_url}/api/datasources/")
        assert resp.status_code == 401


class TestPipelines:
    @pytest.fixture(scope="class")
    def datasource_id(self, base_url, auth_headers):
        resp = requests.post(
            f"{base_url}/api/datasources/",
            headers=auth_headers,
            json={
                "name": "Pipeline Test Source",
                "type": "CSV",
                "file_path": "/tmp/pipeline.csv",
            },
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_get_all_pipelines(self, base_url, auth_headers):
        resp = requests.get(f"{base_url}/api/pipelines/", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_pipeline(self, base_url, auth_headers, datasource_id):
        resp = requests.post(
            f"{base_url}/api/pipelines/",
            headers=auth_headers,
            json={"name": "QA Pipeline", "data_source": datasource_id},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "QA Pipeline"
        assert data["status"] == "PENDING"

    def test_run_pipeline(self, base_url, auth_headers, datasource_id):
        create_resp = requests.post(
            f"{base_url}/api/pipelines/",
            headers=auth_headers,
            json={"name": "Run Test Pipeline", "data_source": datasource_id},
        )
        assert create_resp.status_code == 201
        pipeline_id = create_resp.json()["id"]

        run_resp = requests.post(
            f"{base_url}/api/pipelines/{pipeline_id}/run",
            headers=auth_headers,
        )
        assert run_resp.status_code == 200
        assert run_resp.json()["status"] in ("COMPLETED", "FAILED")

    def test_get_pipelines_unauthenticated(self, base_url):
        resp = requests.get(f"{base_url}/api/pipelines/")
        assert resp.status_code == 401
