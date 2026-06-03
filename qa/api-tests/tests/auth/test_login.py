import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

LOGIN_URL = "/api/auth/login/"


@pytest.mark.django_db
class TestLoginSuccess:
    """Happy-path tests for the login endpoint."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User",
        )
        self.credentials = {"email": "test@example.com", "password": "TestPass123!"}

    def test_login_returns_200(self):
        response = self.client.post(LOGIN_URL, self.credentials, format="json")
        assert response.status_code == 200

    def test_login_response_has_message(self):
        response = self.client.post(LOGIN_URL, self.credentials, format="json")
        assert response.data["message"] == "Login successful"

    def test_login_response_has_user(self):
        response = self.client.post(LOGIN_URL, self.credentials, format="json")
        assert "user" in response.data

    def test_login_response_has_tokens(self):
        response = self.client.post(LOGIN_URL, self.credentials, format="json")
        assert "tokens" in response.data

    def test_login_response_has_access_token(self):
        response = self.client.post(LOGIN_URL, self.credentials, format="json")
        assert "access" in response.data["tokens"]
        assert isinstance(response.data["tokens"]["access"], str)
        assert len(response.data["tokens"]["access"]) > 0

    def test_login_response_has_refresh_token(self):
        response = self.client.post(LOGIN_URL, self.credentials, format="json")
        assert "refresh" in response.data["tokens"]
        assert isinstance(response.data["tokens"]["refresh"], str)
        assert len(response.data["tokens"]["refresh"]) > 0

    def test_login_response_user_fields(self):
        response = self.client.post(LOGIN_URL, self.credentials, format="json")
        user = response.data["user"]
        assert user["email"] == "test@example.com"
        assert user["username"] == "testuser"
        assert user["first_name"] == "Test"
        assert user["last_name"] == "User"
        assert "id" in user
        assert "is_active" in user
        assert "role" in user

    def test_login_user_is_active_in_response(self):
        response = self.client.post(LOGIN_URL, self.credentials, format="json")
        assert response.data["user"]["is_active"] is True

    def test_login_password_not_in_response(self):
        response = self.client.post(LOGIN_URL, self.credentials, format="json")
        assert "password" not in response.data
        assert "password" not in response.data.get("user", {})

    def test_login_tokens_are_jwt_format(self):
        response = self.client.post(LOGIN_URL, self.credentials, format="json")
        access = response.data["tokens"]["access"]
        refresh = response.data["tokens"]["refresh"]
        assert access.count(".") == 2
        assert refresh.count(".") == 2

    def test_login_access_token_authenticates_protected_endpoint(self):
        response = self.client.post(LOGIN_URL, self.credentials, format="json")
        access = response.data["tokens"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        logout_response = self.client.post(
            "/api/auth/logout/",
            {"refresh": response.data["tokens"]["refresh"]},
            format="json",
        )
        assert logout_response.status_code == 200


@pytest.mark.django_db
class TestLoginValidation:
    """Validation and error-path tests for the login endpoint."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_wrong_password_returns_400(self):
        response = self.client.post(
            LOGIN_URL,
            {"email": "test@example.com", "password": "WrongPass!"},
            format="json",
        )
        assert response.status_code == 400

    def test_nonexistent_email_returns_400(self):
        response = self.client.post(
            LOGIN_URL,
            {"email": "nobody@example.com", "password": "TestPass123!"},
            format="json",
        )
        assert response.status_code == 400

    def test_inactive_user_returns_400(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            LOGIN_URL,
            {"email": "test@example.com", "password": "TestPass123!"},
            format="json",
        )
        assert response.status_code == 400

    def test_missing_email_returns_400(self):
        response = self.client.post(
            LOGIN_URL, {"password": "TestPass123!"}, format="json"
        )
        assert response.status_code == 400

    def test_missing_password_returns_400(self):
        response = self.client.post(
            LOGIN_URL, {"email": "test@example.com"}, format="json"
        )
        assert response.status_code == 400

    def test_empty_payload_returns_400(self):
        response = self.client.post(LOGIN_URL, {}, format="json")
        assert response.status_code == 400

    def test_invalid_email_format_returns_400(self):
        response = self.client.post(
            LOGIN_URL,
            {"email": "not-an-email", "password": "TestPass123!"},
            format="json",
        )
        assert response.status_code == 400

    def test_wrong_password_does_not_return_tokens(self):
        response = self.client.post(
            LOGIN_URL,
            {"email": "test@example.com", "password": "WrongPass!"},
            format="json",
        )
        assert "tokens" not in response.data

    def test_nonexistent_email_does_not_reveal_which_field_is_wrong(self):
        response_bad_email = self.client.post(
            LOGIN_URL,
            {"email": "nobody@example.com", "password": "TestPass123!"},
            format="json",
        )
        response_bad_pass = self.client.post(
            LOGIN_URL,
            {"email": "test@example.com", "password": "WrongPass!"},
            format="json",
        )
        assert response_bad_email.status_code == response_bad_pass.status_code == 400

    def test_get_method_not_allowed(self):
        response = self.client.get(LOGIN_URL)
        assert response.status_code == 405

    def test_put_method_not_allowed(self):
        response = self.client.put(LOGIN_URL, {}, format="json")
        assert response.status_code == 405
