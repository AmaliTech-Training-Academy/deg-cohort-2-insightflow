"""
Tests for the Customer model in ingestion app.
"""

import pytest
from apps.ingestion.models.base import Customer
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestCustomerModel:
    """Test cases for the Customer model."""

    def setup_method(self):
        """Setup test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass"
        )

    def test_create_customer_with_id(self):
        """Test creating a customer with custom ID."""
        customer = Customer.objects.create(customerId="CUST-000001", userId=self.user)
        assert customer.customerId == "CUST-000001"
        assert customer.userId == self.user

    def test_create_customer_auto_id(self):
        """Test creating a customer with auto-generated ID."""
        customer = Customer.objects.create(userId=self.user)
        assert customer.customerId == "CUST-000001"

    def test_customer_auto_id_increment(self):
        """Test that auto-generated IDs increment correctly."""
        customer1 = Customer.objects.create(userId=self.user)
        customer2 = Customer.objects.create(userId=self.user)
        customer3 = Customer.objects.create(userId=self.user)

        assert customer1.customerId == "CUST-000001"
        assert customer2.customerId == "CUST-000002"
        assert customer3.customerId == "CUST-000003"

    def test_customer_db_table(self):
        """Test that Customer model uses correct database table."""
        assert Customer._meta.db_table == "customer"

    def test_customer_primary_key(self):
        """Test that customerId is the primary key."""
        customer = Customer.objects.create(customerId="CUST-000001", userId=self.user)
        customer2 = Customer.objects.get(pk="CUST-000001")
        assert customer2.customerId == customer.customerId

    def test_customer_foreign_key_to_user(self):
        """Test customer foreign key relationship to user."""
        customer = Customer.objects.create(customerId="CUST-000001", userId=self.user)
        assert customer.userId.username == "testuser"
        assert customer.userId.email == "test@example.com"

    def test_customer_update(self):
        """Test updating a customer."""
        customer = Customer.objects.create(customerId="CUST-000001", userId=self.user)
        new_user = User.objects.create_user(
            username="newuser", email="new@example.com", password="pass"
        )
        customer.userId = new_user
        customer.save()
        updated = Customer.objects.get(customerId="CUST-000001")
        assert updated.userId.username == "newuser"

    def test_customer_deletion_on_user_delete(self):
        """Test that deleting a user cascades to customer."""
        customer = Customer.objects.create(  # noqa: F841
            customerId="CUST-000001", userId=self.user
        )
        self.user.delete()
        assert Customer.objects.filter(customerId="CUST-000001").exists() is False

    def test_customer_id_format(self):
        """Test auto-generated customer ID format."""
        customer = Customer.objects.create(userId=self.user)
        assert customer.customerId.startswith("CUST-")
        assert len(customer.customerId) == 11

    def test_customer_id_max_length(self):
        """Test customer ID max length constraint."""
        id_field = Customer._meta.get_field("customerId")
        assert id_field.max_length == 20

    def test_multiple_customers_different_users(self):
        """Test creating multiple customers with different users."""
        user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="pass"
        )
        user3 = User.objects.create_user(
            username="user3", email="user3@example.com", password="pass"
        )

        customer1 = Customer.objects.create(userId=self.user)
        customer2 = Customer.objects.create(userId=user2)
        customer3 = Customer.objects.create(userId=user3)  # noqa: F841

        assert Customer.objects.count() == 3
        assert customer1.userId != customer2.userId

    def test_customer_string_representation(self):
        """Test customer string representation."""
        customer = Customer.objects.create(customerId="CUST-000001", userId=self.user)
        assert str(customer.customerId) == "CUST-000001"

    def test_customer_without_auto_id_on_save(self):
        """Test customer auto ID generation only on first save."""
        customer = Customer(userId=self.user)
        customer.save()
        first_id = customer.customerId

        customer.save()
        customer.refresh_from_db()
        assert customer.customerId == first_id
