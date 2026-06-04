import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

TOKEN_REFRESH_URL = "/api/auth/token/refresh/"


@pytest.mark.django_db
class TestTokenRefreshSuccess:
    """Happy-path tests for the token refresh endpoint."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        refresh = RefreshToken.for_user(self.user)
        self.refresh_token = str(refresh)
        self.access_token = str(refresh.access_token)

    def test_refresh_valid_token_returns_200(self):
        response = self.client.post(
            TOKEN_REFRESH_URL, {"refresh": self.refresh_token}, format="json"
        )
        assert response.status_code == 200

    def test_refresh_response_has_access_token(self):
        response = self.client.post(
            TOKEN_REFRESH_URL, {"refresh": self.refresh_token}, format="json"
        )
        assert "access" in response.data

    def test_refresh_access_token_is_non_empty_string(self):
        response = self.client.post(
            TOKEN_REFRESH_URL, {"refresh": self.refresh_token}, format="json"
        )
        assert isinstance(response.data["access"], str)
        assert len(response.data["access"]) > 0

    def test_refresh_access_token_is_jwt_format(self):
        response = self.client.post(
            TOKEN_REFRESH_URL, {"refresh": self.refresh_token}, format="json"
        )
        assert response.data["access"].count(".") == 2

    def test_refresh_does_not_require_authentication(self):
        response = self.client.post(
            TOKEN_REFRESH_URL, {"refresh": self.refresh_token}, format="json"
        )
        assert response.status_code == 200

    def test_refresh_new_access_token_authenticates_protected_endpoint(self):
        response = self.client.post(
            TOKEN_REFRESH_URL, {"refresh": self.refresh_token}, format="json"
        )
        new_access = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access}")
        logout_response = self.client.post(
            "/api/auth/logout/",
            {"refresh": self.refresh_token},
            format="json",
        )
        assert logout_response.status_code == 200

    def test_refresh_same_token_can_be_used_multiple_times(self):
        response1 = self.client.post(
            TOKEN_REFRESH_URL, {"refresh": self.refresh_token}, format="json"
        )
        response2 = self.client.post(
            TOKEN_REFRESH_URL, {"refresh": self.refresh_token}, format="json"
        )
        assert response1.status_code == 200
        assert response2.status_code == 200


@pytest.mark.django_db
class TestTokenRefreshValidation:
    """Input validation and error-path tests for the token refresh endpoint."""

    def setup_method(self):
        self.client = APIClient()

    def test_invalid_token_returns_401(self):
        response = self.client.post(
            TOKEN_REFRESH_URL, {"refresh": "invalid.token.here"}, format="json"
        )
        assert response.status_code == 401

    def test_missing_refresh_field_returns_400(self):
        response = self.client.post(TOKEN_REFRESH_URL, {}, format="json")
        assert response.status_code == 400

    def test_random_string_token_returns_401(self):
        response = self.client.post(
            TOKEN_REFRESH_URL, {"refresh": "notavalidjwttoken"}, format="json"
        )
        assert response.status_code == 401

    def test_access_token_used_as_refresh_returns_401(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass"
        )
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        response = self.client.post(
            TOKEN_REFRESH_URL, {"refresh": access_token}, format="json"
        )
        assert response.status_code == 401

    def test_get_method_not_allowed(self):
        response = self.client.get(TOKEN_REFRESH_URL)
        assert response.status_code == 405

    def test_put_method_not_allowed(self):
        response = self.client.put(TOKEN_REFRESH_URL, {}, format="json")
        assert response.status_code == 405
