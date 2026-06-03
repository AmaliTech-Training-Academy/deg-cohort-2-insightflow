"""
Unit tests for POS serializers.

Tests PosTransactionSerializer and PosTransactionLineSerializer for correct
field inclusion, value mapping, and many=True behaviour.
"""

from decimal import Decimal

import pytest
from apps.ingestion.models.inventory import Category, Product, Store
from apps.ingestion.models.pos import Cashier, PosTransaction, PosTransactionLine
from apps.ingestion.serializers.pos import (
    PosTransactionLineSerializer,
    PosTransactionSerializer,
)
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.mark.django_db
class TestPosTransactionSerializer:
    """Tests for PosTransactionSerializer."""

    def setup_method(self):
        self.user = User.objects.create_user(
            username="cashier1", email="cashier@test.com", password="pass"
        )
        self.store = Store.objects.create(
            storeId=1, storeName="Test Store", province="Ontario"
        )
        self.cashier = Cashier.objects.create(
            cashierId=1, storeId=self.store, fullName="Test Cashier", userId=self.user
        )

    def test_all_expected_fields_present(self):
        """Serialized output contains all declared fields."""
        txn = PosTransaction.objects.create(
            posTransactionId=1,
            storeId=self.store,
            cashierId=self.cashier,
            transactionDatetime=timezone.now(),
        )
        data = PosTransactionSerializer(txn).data
        for field in [
            "posTransactionId",
            "storeId",
            "cashierId",
            "transactionDatetime",
        ]:
            assert field in data

    def test_posTransactionId_value_correct(self):
        """posTransactionId is serialized with the correct value."""
        txn = PosTransaction.objects.create(
            posTransactionId=42,
            storeId=self.store,
            cashierId=self.cashier,
            transactionDatetime=timezone.now(),
        )
        data = PosTransactionSerializer(txn).data
        assert data["posTransactionId"] == 42

    def test_storeId_fk_serialized_as_pk(self):
        """storeId FK serializes as the primary key value."""
        txn = PosTransaction.objects.create(
            posTransactionId=1,
            storeId=self.store,
            cashierId=self.cashier,
            transactionDatetime=timezone.now(),
        )
        data = PosTransactionSerializer(txn).data
        assert data["storeId"] == self.store.storeId

    def test_cashierId_fk_serialized_as_pk(self):
        """cashierId FK serializes as the primary key value."""
        txn = PosTransaction.objects.create(
            posTransactionId=1,
            storeId=self.store,
            cashierId=self.cashier,
            transactionDatetime=timezone.now(),
        )
        data = PosTransactionSerializer(txn).data
        assert data["cashierId"] == self.cashier.cashierId

    def test_many_true_returns_list(self):
        """many=True wraps multiple transactions in a list."""
        for i in range(1, 4):
            PosTransaction.objects.create(
                posTransactionId=i,
                storeId=self.store,
                cashierId=self.cashier,
                transactionDatetime=timezone.now(),
            )
        qs = PosTransaction.objects.all()
        data = PosTransactionSerializer(qs, many=True).data
        assert len(data) == 3


@pytest.mark.django_db
class TestPosTransactionLineSerializer:
    """Tests for PosTransactionLineSerializer."""

    def setup_method(self):
        self.user = User.objects.create_user(
            username="cashier1", email="cashier@test.com", password="pass"
        )
        self.store = Store.objects.create(
            storeId=1, storeName="Test Store", province="Ontario"
        )
        self.cashier = Cashier.objects.create(
            cashierId=1, storeId=self.store, fullName="Test Cashier", userId=self.user
        )
        self.transaction = PosTransaction.objects.create(
            posTransactionId=1,
            storeId=self.store,
            cashierId=self.cashier,
            transactionDatetime=timezone.now(),
        )
        self.category = Category.objects.create(categoryId=1, name="Electronics")
        self.product = Product.objects.create(
            productSKU="PROD-0000001", productName="Laptop", categoryId=self.category
        )

    def _make_line(
        self, line_id=1, quantity=2, unit_price="25.00", discount="0.00", total="50.00"
    ):
        return PosTransactionLine.objects.create(
            lineId=line_id,
            posTransactionId=self.transaction,
            productSKU=self.product,
            quantity=quantity,
            unitPrice=Decimal(unit_price),
            discountApplied=Decimal(discount),
            totalAmount=Decimal(total),
        )

    def test_all_expected_fields_present(self):
        """Serialized output contains all declared fields."""
        line = self._make_line()
        data = PosTransactionLineSerializer(line).data
        for field in [
            "lineId",
            "posTransactionId",
            "productSKU",
            "quantity",
            "unitPrice",
            "discountApplied",
            "totalAmount",
        ]:
            assert field in data

    def test_lineId_value_correct(self):
        """lineId is serialized with the correct value."""
        line = self._make_line(line_id=7)
        data = PosTransactionLineSerializer(line).data
        assert data["lineId"] == 7

    def test_quantity_value_correct(self):
        """quantity is serialized with the correct integer value."""
        line = self._make_line(quantity=5)
        data = PosTransactionLineSerializer(line).data
        assert data["quantity"] == 5

    def test_decimal_fields_serialized_correctly(self):
        """unitPrice, discountApplied, and totalAmount serialize to correct decimals."""
        line = self._make_line(unit_price="25.50", discount="2.50", total="48.50")
        data = PosTransactionLineSerializer(line).data
        assert Decimal(data["unitPrice"]) == Decimal("25.50")
        assert Decimal(data["discountApplied"]) == Decimal("2.50")
        assert Decimal(data["totalAmount"]) == Decimal("48.50")

    def test_posTransactionId_fk_serialized_as_pk(self):
        """posTransactionId FK serializes as the transaction's PK."""
        line = self._make_line()
        data = PosTransactionLineSerializer(line).data
        assert data["posTransactionId"] == self.transaction.posTransactionId

    def test_productSKU_fk_serialized_as_pk(self):
        """productSKU FK serializes as the product's SKU string."""
        line = self._make_line()
        data = PosTransactionLineSerializer(line).data
        assert data["productSKU"] == self.product.productSKU

    def test_zero_discount_accepted(self):
        """discountApplied of 0 serializes without error."""
        line = self._make_line(discount="0.00")
        data = PosTransactionLineSerializer(line).data
        assert Decimal(data["discountApplied"]) == Decimal("0.00")

    def test_many_true_returns_list_of_correct_length(self):
        """many=True serializes all lines for a transaction."""
        for i in range(1, 4):
            self._make_line(line_id=i)
        qs = PosTransactionLine.objects.filter(posTransactionId=self.transaction)
        data = PosTransactionLineSerializer(qs, many=True).data
        assert len(data) == 3
