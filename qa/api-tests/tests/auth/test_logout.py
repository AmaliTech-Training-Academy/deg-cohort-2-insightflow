import pytest
from apps.authentication.models import TokenBlacklist
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

LOGOUT_URL = "/api/auth/logout/"


def _get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


@pytest.mark.django_db
class TestLogoutSuccess:
    """Happy-path tests for the logout endpoint."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        self.tokens = _get_tokens(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens['access']}")

    def test_logout_returns_200(self):
        response = self.client.post(
            LOGOUT_URL, {"refresh": self.tokens["refresh"]}, format="json"
        )
        assert response.status_code == 200

    def test_logout_response_has_message(self):
        response = self.client.post(
            LOGOUT_URL, {"refresh": self.tokens["refresh"]}, format="json"
        )
        assert response.data["message"] == "Logout successful"

    def test_logout_creates_blacklist_entry(self):
        self.client.post(LOGOUT_URL, {"refresh": self.tokens["refresh"]}, format="json")
        assert TokenBlacklist.objects.filter(user=self.user).exists()

    def test_logout_blacklist_entry_stores_correct_token(self):
        self.client.post(LOGOUT_URL, {"refresh": self.tokens["refresh"]}, format="json")
        entry = TokenBlacklist.objects.get(user=self.user)
        assert entry.token == self.tokens["refresh"]

    def test_logout_blacklist_entry_has_expiry(self):
        self.client.post(LOGOUT_URL, {"refresh": self.tokens["refresh"]}, format="json")
        entry = TokenBlacklist.objects.get(user=self.user)
        assert entry.expires_at is not None

    def test_logout_blacklist_entry_links_to_correct_user(self):
        self.client.post(LOGOUT_URL, {"refresh": self.tokens["refresh"]}, format="json")
        entry = TokenBlacklist.objects.get(user=self.user)
        assert entry.user == self.user

    def test_logout_multiple_sessions_each_create_blacklist_entry(self):
        tokens2 = _get_tokens(self.user)
        self.client.post(LOGOUT_URL, {"refresh": self.tokens["refresh"]}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens2['access']}")
        self.client.post(LOGOUT_URL, {"refresh": tokens2["refresh"]}, format="json")
        assert TokenBlacklist.objects.filter(user=self.user).count() == 2

    def test_logout_different_users_separate_blacklist_entries(self):
        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="OtherPass123!",
        )
        other_tokens = _get_tokens(other_user)
        self.client.post(LOGOUT_URL, {"refresh": self.tokens["refresh"]}, format="json")
        other_client = APIClient()
        other_client.credentials(HTTP_AUTHORIZATION=f"Bearer {other_tokens['access']}")
        other_client.post(
            LOGOUT_URL, {"refresh": other_tokens["refresh"]}, format="json"
        )
        assert TokenBlacklist.objects.filter(user=self.user).count() == 1
        assert TokenBlacklist.objects.filter(user=other_user).count() == 1


@pytest.mark.django_db
class TestLogoutAuthRequired:
    """Tests verifying logout enforces authentication."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        self.tokens = _get_tokens(self.user)

    def test_logout_without_auth_header_returns_401(self):
        response = self.client.post(
            LOGOUT_URL, {"refresh": self.tokens["refresh"]}, format="json"
        )
        assert response.status_code == 401

    def test_logout_with_invalid_access_token_returns_401(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid.access.token")
        response = self.client.post(
            LOGOUT_URL, {"refresh": self.tokens["refresh"]}, format="json"
        )
        assert response.status_code == 401

    def test_logout_with_wrong_auth_scheme_returns_401(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.tokens['access']}")
        response = self.client.post(
            LOGOUT_URL, {"refresh": self.tokens["refresh"]}, format="json"
        )
        assert response.status_code == 401

    def test_logout_unauthenticated_does_not_create_blacklist_entry(self):
        self.client.post(LOGOUT_URL, {"refresh": self.tokens["refresh"]}, format="json")
        assert TokenBlacklist.objects.filter(user=self.user).exists() is False


@pytest.mark.django_db
class TestLogoutValidation:
    """Input validation tests for the logout endpoint."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        self.tokens = _get_tokens(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens['access']}")

    def test_logout_invalid_refresh_token_returns_400(self):
        response = self.client.post(
            LOGOUT_URL, {"refresh": "totally.invalid.token"}, format="json"
        )
        assert response.status_code == 400

    def test_logout_missing_refresh_field_returns_400(self):
        response = self.client.post(LOGOUT_URL, {}, format="json")
        assert response.status_code == 400

    def test_logout_malformed_token_does_not_create_blacklist_entry(self):
        self.client.post(
            LOGOUT_URL, {"refresh": "totally.invalid.token"}, format="json"
        )
        assert TokenBlacklist.objects.filter(user=self.user).exists() is False

    def test_logout_get_method_not_allowed(self):
        response = self.client.get(LOGOUT_URL)
        assert response.status_code == 405
