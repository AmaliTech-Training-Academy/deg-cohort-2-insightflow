"""
Tests for POS models (Cashier, PosTransaction, PosTransactionLine).
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.ingestion.models.inventory import Store, Category, Product
from apps.ingestion.models.pos import Cashier, PosTransaction, PosTransactionLine

User = get_user_model()


@pytest.mark.django_db
class TestCashierModel:
    """Test cases for the Cashier model."""

    def setup_method(self):
        """Setup test data."""
        self.user = User.objects.create_user(
            username="cashier1", email="cashier@example.com", password="pass"
        )
        self.store = Store.objects.create(
            storeId=1, storeName="Downtown", province="Ontario"
        )

    def test_create_cashier(self):
        """Test creating a cashier."""
        cashier = Cashier.objects.create(
            cashierId=1, storeId=self.store, fullName="John Doe", userId=self.user
        )
        assert cashier.cashierId == 1
        assert cashier.storeId == self.store
        assert cashier.fullName == "John Doe"
        assert cashier.userId == self.user

    def test_cashier_db_table(self):
        """Test that Cashier model uses correct database table."""
        assert Cashier._meta.db_table == "cashier"

    def test_cashier_primary_key(self):
        """Test that cashierId is the primary key."""
        cashier = Cashier.objects.create(
            cashierId=1, storeId=self.store, fullName="John Doe", userId=self.user
        )
        cashier2 = Cashier.objects.get(pk=1)
        assert cashier2.cashierId == cashier.cashierId

    def test_cashier_full_name_constraint(self):
        """Test cashier full name field constraints."""
        fullname_field = Cashier._meta.get_field("fullName")
        assert fullname_field.max_length == 255

    def test_cashier_foreign_keys(self):
        """Test cashier foreign key relationships."""
        cashier = Cashier.objects.create(
            cashierId=1, storeId=self.store, fullName="John Doe", userId=self.user
        )
        assert cashier.storeId.storeId == 1
        assert cashier.userId.username == "cashier1"

    def test_cashier_deletion_cascade_on_store(self):
        """Test deleting a store cascades to cashiers."""
        cashier = Cashier.objects.create(
            cashierId=1, storeId=self.store, fullName="John Doe", userId=self.user
        )
        self.store.delete()
        assert Cashier.objects.filter(cashierId=1).exists() is False

    def test_cashier_deletion_cascade_on_user(self):
        """Test deleting a user cascades to cashiers."""
        cashier = Cashier.objects.create(
            cashierId=1, storeId=self.store, fullName="John Doe", userId=self.user
        )
        self.user.delete()
        assert Cashier.objects.filter(cashierId=1).exists() is False

    def test_multiple_cashiers_same_store(self):
        """Test creating multiple cashiers for same store."""
        user2 = User.objects.create_user(
            username="cashier2", email="cashier2@example.com", password="pass"
        )
        Cashier.objects.create(
            cashierId=1, storeId=self.store, fullName="John Doe", userId=self.user
        )
        Cashier.objects.create(
            cashierId=2, storeId=self.store, fullName="Jane Smith", userId=user2
        )
        assert Cashier.objects.filter(storeId=self.store).count() == 2


@pytest.mark.django_db
class TestPosTransactionModel:
    """Test cases for the PosTransaction model."""

    def setup_method(self):
        """Setup test data."""
        self.user = User.objects.create_user(
            username="cashier1", email="cashier@example.com", password="pass"
        )
        self.store = Store.objects.create(
            storeId=1, storeName="Downtown", province="Ontario"
        )
        self.cashier = Cashier.objects.create(
            cashierId=1, storeId=self.store, fullName="John Doe", userId=self.user
        )

    def test_create_pos_transaction(self):
        """Test creating a POS transaction."""
        transaction = PosTransaction.objects.create(
            posTransactionId=1,
            storeId=self.store,
            cashierId=self.cashier,
            transactionDatetime=timezone.now(),
        )
        assert transaction.posTransactionId == 1
        assert transaction.storeId == self.store
        assert transaction.cashierId == self.cashier

    def test_pos_transaction_db_table(self):
        """Test that PosTransaction model uses correct database table."""
        assert PosTransaction._meta.db_table == "posTransaction"

    def test_pos_transaction_primary_key(self):
        """Test that posTransactionId is the primary key."""
        transaction = PosTransaction.objects.create(
            posTransactionId=1,
            storeId=self.store,
            cashierId=self.cashier,
            transactionDatetime=timezone.now(),
        )
        trans2 = PosTransaction.objects.get(pk=1)
        assert trans2.posTransactionId == transaction.posTransactionId

    def test_pos_transaction_foreign_keys(self):
        """Test POS transaction foreign key relationships."""
        transaction = PosTransaction.objects.create(
            posTransactionId=1,
            storeId=self.store,
            cashierId=self.cashier,
            transactionDatetime=timezone.now(),
        )
        assert transaction.storeId.storeId == 1
        assert transaction.cashierId.cashierId == 1

    def test_pos_transaction_deletion_cascade_on_store(self):
        """Test deleting a store cascades to transactions."""
        transaction = PosTransaction.objects.create(
            posTransactionId=1,
            storeId=self.store,
            cashierId=self.cashier,
            transactionDatetime=timezone.now(),
        )
        self.store.delete()
        assert PosTransaction.objects.filter(posTransactionId=1).exists() is False

    def test_pos_transaction_deletion_cascade_on_cashier(self):
        """Test deleting a cashier cascades to transactions."""
        transaction = PosTransaction.objects.create(
            posTransactionId=1,
            storeId=self.store,
            cashierId=self.cashier,
            transactionDatetime=timezone.now(),
        )
        self.cashier.delete()
        assert PosTransaction.objects.filter(posTransactionId=1).exists() is False

    def test_multiple_transactions_same_store(self):
        """Test creating multiple transactions for same store."""
        for i in range(1, 4):
            PosTransaction.objects.create(
                posTransactionId=i,
                storeId=self.store,
                cashierId=self.cashier,
                transactionDatetime=timezone.now(),
            )
        assert PosTransaction.objects.filter(storeId=self.store).count() == 3


@pytest.mark.django_db
class TestPosTransactionLineModel:
    """Test cases for the PosTransactionLine model."""

    def setup_method(self):
        """Setup test data."""
        self.user = User.objects.create_user(
            username="cashier1", email="cashier@example.com", password="pass"
        )
        self.store = Store.objects.create(
            storeId=1, storeName="Downtown", province="Ontario"
        )
        self.cashier = Cashier.objects.create(
            cashierId=1, storeId=self.store, fullName="John Doe", userId=self.user
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

    def test_create_pos_transaction_line(self):
        """Test creating a POS transaction line."""
        line = PosTransactionLine.objects.create(
            lineId=1,
            posTransactionId=self.transaction,
            productSKU=self.product,
            quantity=1,
            unitPrice=Decimal("999.99"),
            discountApplied=Decimal("0.00"),
            totalAmount=Decimal("999.99"),
        )
        assert line.lineId == 1
        assert line.posTransactionId == self.transaction
        assert line.productSKU == self.product
        assert line.quantity == 1

    def test_pos_transaction_line_db_table(self):
        """Test that PosTransactionLine model uses correct database table."""
        assert PosTransactionLine._meta.db_table == "posTransactionLine"

    def test_pos_transaction_line_primary_key(self):
        """Test that lineId is the primary key."""
        line = PosTransactionLine.objects.create(
            lineId=1,
            posTransactionId=self.transaction,
            productSKU=self.product,
            quantity=1,
            unitPrice=Decimal("999.99"),
            discountApplied=Decimal("0.00"),
            totalAmount=Decimal("999.99"),
        )
        line2 = PosTransactionLine.objects.get(pk=1)
        assert line2.lineId == line.lineId

    def test_pos_transaction_line_decimal_fields(self):
        """Test decimal field handling."""
        line = PosTransactionLine.objects.create(
            lineId=1,
            posTransactionId=self.transaction,
            productSKU=self.product,
            quantity=2,
            unitPrice=Decimal("50.00"),
            discountApplied=Decimal("5.00"),
            totalAmount=Decimal("95.00"),
        )
        assert isinstance(line.unitPrice, Decimal)
        assert isinstance(line.discountApplied, Decimal)
        assert isinstance(line.totalAmount, Decimal)
        assert line.quantity == 2

    def test_pos_transaction_line_foreign_keys(self):
        """Test foreign key relationships."""
        line = PosTransactionLine.objects.create(
            lineId=1,
            posTransactionId=self.transaction,
            productSKU=self.product,
            quantity=1,
            unitPrice=Decimal("999.99"),
            discountApplied=Decimal("0.00"),
            totalAmount=Decimal("999.99"),
        )
        assert line.posTransactionId.posTransactionId == 1
        assert line.productSKU.productSKU == "PROD-0000001"

    def test_pos_transaction_line_deletion_cascade(self):
        """Test deleting a transaction cascades to lines."""
        line = PosTransactionLine.objects.create(
            lineId=1,
            posTransactionId=self.transaction,
            productSKU=self.product,
            quantity=1,
            unitPrice=Decimal("999.99"),
            discountApplied=Decimal("0.00"),
            totalAmount=Decimal("999.99"),
        )
        self.transaction.delete()
        assert PosTransactionLine.objects.filter(lineId=1).exists() is False

    def test_multiple_lines_per_transaction(self):
        """Test creating multiple lines for one transaction."""
        for i in range(1, 4):
            product = Product.objects.create(
                productName=f"Product {i}", categoryId=self.category
            )
            PosTransactionLine.objects.create(
                lineId=i,
                posTransactionId=self.transaction,
                productSKU=product,
                quantity=i,
                unitPrice=Decimal(f"{10 * i}.00"),
                discountApplied=Decimal("0.00"),
                totalAmount=Decimal(f"{10 * i}.00"),
            )
        assert PosTransactionLine.objects.filter(
            posTransactionId=self.transaction
        ).count() == 3

    def test_pos_transaction_line_product_deletion(self):
        """Test deleting a product cascades to transaction lines."""
        line = PosTransactionLine.objects.create(
            lineId=1,
            posTransactionId=self.transaction,
            productSKU=self.product,
            quantity=1,
            unitPrice=Decimal("999.99"),
            discountApplied=Decimal("0.00"),
            totalAmount=Decimal("999.99"),
        )
        self.product.delete()
        assert PosTransactionLine.objects.filter(lineId=1).exists() is False
