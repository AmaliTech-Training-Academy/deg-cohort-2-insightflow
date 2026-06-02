"""
Tests for the core models.
"""

import pytest
from apps.core.models import TimeStampedModel
from apps.ingestion.models.inventory import Store
from django.db import models
from django.utils import timezone


@pytest.mark.django_db
class TestTimeStampedModel:
    """Test cases for the TimeStampedModel abstract base class."""

    def test_timestamped_model_is_abstract(self):
        """Test that TimeStampedModel is abstract."""
        assert TimeStampedModel._meta.abstract is True

    def test_timestamped_model_has_created_at(self):
        """Test that TimeStampedModel has created_at field."""
        assert hasattr(TimeStampedModel, "created_at")
        field = TimeStampedModel._meta.get_field("created_at")
        assert isinstance(field, models.DateTimeField)

    def test_timestamped_model_has_updated_at(self):
        """Test that TimeStampedModel has updated_at field."""
        assert hasattr(TimeStampedModel, "updated_at")
        field = TimeStampedModel._meta.get_field("updated_at")
        assert isinstance(field, models.DateTimeField)

    def test_created_at_auto_now_add(self):
        """Test that created_at uses auto_now_add."""
        field = TimeStampedModel._meta.get_field("created_at")
        assert field.auto_now_add is True
        assert field.auto_now is False

    def test_updated_at_auto_now(self):
        """Test that updated_at uses auto_now."""
        field = TimeStampedModel._meta.get_field("updated_at")
        assert field.auto_now is True
        assert field.auto_now_add is False

    def test_created_at_not_null(self):
        """Test that created_at is not null."""
        field = TimeStampedModel._meta.get_field("created_at")
        assert field.null is False

    def test_updated_at_not_null(self):
        """Test that updated_at is not null."""
        field = TimeStampedModel._meta.get_field("updated_at")
        assert field.null is False

    def test_concrete_model_inherits_timestamps(self):

        assert hasattr(Store, "created_at")
        assert hasattr(Store, "updated_at")

    def test_concrete_model_timestamps_work(self):
        """Test that timestamps work on concrete model instances."""

        store = Store.objects.create(storeId=1, storeName="Test Store", province="Test")
        assert store.created_at is not None
        assert store.updated_at is not None
        assert isinstance(store.created_at, type(timezone.now()))
        assert isinstance(store.updated_at, type(timezone.now()))

    def test_updated_at_changes_on_save(self):
        """Test that updated_at changes when model is saved."""

        store = Store.objects.create(storeId=1, storeName="Test Store", province="Test")
        original_updated = store.updated_at
        created = store.created_at

        import time

        time.sleep(0.1)

        store.storeName = "Updated Store"
        store.save()

        store.refresh_from_db()
        assert store.updated_at > original_updated
        assert store.created_at == created

    def test_created_at_does_not_change_on_update(self):
        """Test that created_at does not change when model is updated."""

        store = Store.objects.create(storeId=1, storeName="Test Store", province="Test")
        original_created = store.created_at

        import time

        time.sleep(0.1)

        store.storeName = "Updated Store"
        store.save()

        store.refresh_from_db()
        assert store.created_at == original_created
