"""
Tests for the User model in authentication app.
"""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Test cases for the User model."""

    def test_create_user_basic(self):
        """Test creating a basic user."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.id is not None

    def test_create_user_with_role(self):
        """Test creating a user with a role."""
        user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="admin123",
            role="admin",
        )
        assert user.role == "admin"
        assert user.username == "admin"

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            username="superuser", email="super@example.com", password="super123"
        )
        assert user.is_superuser is True
        assert user.is_staff is True

    def test_user_is_active_by_default(self):
        """Test that new users are active by default."""
        user = User.objects.create_user(
            username="activeuser", email="active@example.com", password="pass123"
        )
        assert user.is_active is True

    def test_user_db_table_name(self):
        """Test that the User model uses correct database table."""
        assert User._meta.db_table == "users"

    def test_user_string_representation(self):
        """Test user string representation."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass"
        )
        assert str(user) == "testuser"

    def test_user_has_usable_password(self):
        """Test that user password is properly hashed."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        assert user.has_usable_password()

    def test_user_password_verification(self):
        """Test password verification."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        assert user.check_password("testpass123") is True
        assert user.check_password("wrongpass") is False

    def test_user_update_role(self):
        """Test updating user role."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass", role="user"
        )
        user.role = "manager"
        user.save()
        updated_user = User.objects.get(username="testuser")
        assert updated_user.role == "manager"

    def test_user_id_is_big_auto_field(self):
        """Test that user ID is a BigAutoField."""
        id_field = User._meta.get_field("id")
        assert id_field.get_internal_type() == "BigAutoField"

    def test_multiple_users_creation(self):
        """Test creating multiple users."""
        users_data = [
            {"username": "user1", "email": "user1@example.com", "password": "pass1"},
            {"username": "user2", "email": "user2@example.com", "password": "pass2"},
            {"username": "user3", "email": "user3@example.com", "password": "pass3"},
        ]

        for data in users_data:
            User.objects.create_user(**data)

        assert User.objects.count() == 3

    def test_user_last_login_tracking(self):
        """Test that last_login field can be set."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass"
        )
        assert user.last_login is None

    def test_user_is_staff_default(self):
        """Test that is_staff is False by default for regular users."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass"
        )
        assert user.is_staff is False

    def test_user_role_nullable(self):
        """Test that user role can be null."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass"
        )
        assert user.role is None

    def test_user_role_blank(self):
        """Test that user role allows blank values."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass", role=""
        )
        assert user.role == ""

    def test_user_deletion(self):
        """Test user deletion."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass"
        )
        user_id = user.id
        user.delete()
        assert User.objects.filter(id=user_id).exists() is False

    def test_user_update_email(self):
        """Test updating user email."""
        user = User.objects.create_user(
            username="testuser", email="old@example.com", password="pass"
        )
        user.email = "new@example.com"
        user.save()
        updated_user = User.objects.get(username="testuser")
        assert updated_user.email == "new@example.com"

    def test_user_get_full_name(self):
        """Test getting user full name."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass"
        )
        user.first_name = "John"
        user.last_name = "Doe"
        user.save()
        assert user.get_full_name() == "John Doe"

    def test_user_get_short_name(self):
        """Test getting user short name."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass"
        )
        user.first_name = "John"
        user.save()
        assert user.get_short_name() == "John"
