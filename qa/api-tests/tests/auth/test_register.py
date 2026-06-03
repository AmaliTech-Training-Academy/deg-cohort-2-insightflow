import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

REGISTER_URL = "/api/auth/register/"

VALID_PAYLOAD = {
    "email": "john@example.com",
    "username": "johndoe",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
}


@pytest.mark.django_db
class TestRegisterSuccess:
    """Happy-path tests for the register endpoint."""

    def setup_method(self):
        self.client = APIClient()

    def test_register_returns_201(self):
        response = self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        assert response.status_code == 201

    def test_register_response_has_message(self):
        response = self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        assert response.data["message"] == "User registered successfully"

    def test_register_response_has_user(self):
        response = self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        assert "user" in response.data

    def test_register_response_user_fields(self):
        response = self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        user = response.data["user"]
        assert user["email"] == "john@example.com"
        assert user["username"] == "johndoe"
        assert user["first_name"] == "John"
        assert user["last_name"] == "Doe"
        assert "id" in user
        assert "is_active" in user
        assert "role" in user

    def test_register_user_is_active_by_default(self):
        response = self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        assert response.data["user"]["is_active"] is True

    def test_register_role_is_none_by_default(self):
        response = self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        assert response.data["user"]["role"] is None

    def test_register_password_not_in_response(self):
        response = self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        assert "password" not in response.data
        assert "password" not in response.data.get("user", {})

    def test_register_creates_user_in_db(self):
        self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        assert User.objects.filter(email="john@example.com").exists()

    def test_register_user_id_is_integer(self):
        response = self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        assert isinstance(response.data["user"]["id"], int)

    def test_register_role_field_is_ignored_in_request(self):
        payload = {**VALID_PAYLOAD, "role": "admin"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 201
        assert response.data["user"]["role"] is None

    def test_register_password_is_hashed_in_db(self):
        self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        user = User.objects.get(email="john@example.com")
        assert user.check_password("SecurePass123!") is True
        assert user.password != "SecurePass123!"


@pytest.mark.django_db
class TestRegisterValidation:
    """Validation and error-path tests for the register endpoint."""

    def setup_method(self):
        self.client = APIClient()
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="pass123",
            first_name="Existing",
            last_name="User",
        )

    def test_duplicate_email_returns_400(self):
        payload = {**VALID_PAYLOAD, "email": "existing@example.com"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_duplicate_username_returns_400(self):
        payload = {**VALID_PAYLOAD, "username": "existing"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_missing_first_name_returns_400(self):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "first_name"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_missing_last_name_returns_400(self):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "last_name"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_missing_email_returns_400(self):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "email"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_missing_username_returns_400(self):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "username"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_missing_password_returns_400(self):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "password"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_invalid_email_format_returns_400(self):
        payload = {**VALID_PAYLOAD, "email": "not-a-valid-email"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_empty_payload_returns_400(self):
        response = self.client.post(REGISTER_URL, {}, format="json")
        assert response.status_code == 400

    def test_get_method_not_allowed(self):
        response = self.client.get(REGISTER_URL)
        assert response.status_code == 405

    def test_put_method_not_allowed(self):
        response = self.client.put(REGISTER_URL, VALID_PAYLOAD, format="json")
        assert response.status_code == 405

    def test_duplicate_email_does_not_create_user(self):
        payload = {**VALID_PAYLOAD, "email": "existing@example.com"}
        self.client.post(REGISTER_URL, payload, format="json")
        assert User.objects.filter(email="existing@example.com").count() == 1

    def test_password_too_short_returns_400(self):
        payload = {**VALID_PAYLOAD, "password": "Ab1!"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_password_no_uppercase_returns_400(self):
        payload = {**VALID_PAYLOAD, "password": "securepass123!"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_password_no_lowercase_returns_400(self):
        payload = {**VALID_PAYLOAD, "password": "SECUREPASS123!"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_password_no_digit_returns_400(self):
        payload = {**VALID_PAYLOAD, "password": "SecurePass!!!"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_password_no_special_char_returns_400(self):
        payload = {**VALID_PAYLOAD, "password": "SecurePass123"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_weak_password_does_not_create_user(self):
        payload = {**VALID_PAYLOAD, "password": "password"}
        self.client.post(REGISTER_URL, payload, format="json")
        assert User.objects.filter(email=VALID_PAYLOAD["email"]).exists() is False
