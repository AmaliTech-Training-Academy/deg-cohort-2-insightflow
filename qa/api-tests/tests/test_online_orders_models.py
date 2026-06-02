"""
Tests for online order models (OnlineOrder, OnlineOrderLine).
"""

from decimal import Decimal

import pytest
from apps.ingestion.models.base import Customer
from apps.ingestion.models.inventory import Category, Product
from apps.ingestion.models.online_orders import OnlineOrder, OnlineOrderLine
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.mark.django_db
class TestOnlineOrderModel:
    """Test cases for the OnlineOrder model."""

    def setup_method(self):
        """Setup test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass"
        )
        self.customer = Customer.objects.create(
            customerId="CUST-000001", userId=self.user
        )

    def test_create_online_order(self):
        """Test creating an online order."""
        order = OnlineOrder.objects.create(
            onlineOrderId=1,
            customerId=self.customer,
            orderDatetime=timezone.now(),
            shippingProvince="Ontario",
            orderStatus="pending",
            paymentMethod="credit_card",
        )
        assert order.onlineOrderId == 1
        assert order.customerId == self.customer
        assert order.shippingProvince == "Ontario"
        assert order.orderStatus == "pending"

    def test_online_order_db_table(self):
        """Test that OnlineOrder model uses correct database table."""
        assert OnlineOrder._meta.db_table == "onlineOrder"

    def test_online_order_primary_key(self):
        """Test that onlineOrderId is the primary key."""
        order = OnlineOrder.objects.create(
            onlineOrderId=1,
            customerId=self.customer,
            orderDatetime=timezone.now(),
            shippingProvince="Ontario",
            orderStatus="pending",
            paymentMethod="credit_card",
        )
        order2 = OnlineOrder.objects.get(pk=1)
        assert order2.onlineOrderId == order.onlineOrderId

    def test_online_order_status_change(self):
        """Test changing order status."""
        order = OnlineOrder.objects.create(
            onlineOrderId=1,
            customerId=self.customer,
            orderDatetime=timezone.now(),
            shippingProvince="Ontario",
            orderStatus="pending",
            paymentMethod="credit_card",
        )
        order.orderStatus = "shipped"
        order.save()
        updated = OnlineOrder.objects.get(onlineOrderId=1)
        assert updated.orderStatus == "shipped"

    def test_online_order_foreign_key_to_customer(self):
        """Test order foreign key relationship to customer."""
        order = OnlineOrder.objects.create(
            onlineOrderId=1,
            customerId=self.customer,
            orderDatetime=timezone.now(),
            shippingProvince="Ontario",
            orderStatus="pending",
            paymentMethod="credit_card",
        )
        assert order.customerId.customerId == "CUST-000001"

    def test_online_order_deletion_cascade(self):
        """Test deleting a customer cascades to orders."""
        order = OnlineOrder.objects.create(  # noqa F841
            onlineOrderId=1,
            customerId=self.customer,
            orderDatetime=timezone.now(),
            shippingProvince="Ontario",
            orderStatus="pending",
            paymentMethod="credit_card",
        )
        self.customer.delete()
        assert OnlineOrder.objects.filter(onlineOrderId=1).exists() is False

    def test_multiple_orders_same_customer(self):
        """Test creating multiple orders for same customer."""
        for i in range(1, 4):
            OnlineOrder.objects.create(
                onlineOrderId=i,
                customerId=self.customer,
                orderDatetime=timezone.now(),
                shippingProvince="Ontario",
                orderStatus="pending",
                paymentMethod="credit_card",
            )
        assert OnlineOrder.objects.filter(customerId=self.customer).count() == 3

    def test_online_order_fields_max_length(self):
        """Test online order fields constraints."""
        province_field = OnlineOrder._meta.get_field("shippingProvince")
        assert province_field.max_length == 255

        status_field = OnlineOrder._meta.get_field("orderStatus")
        assert status_field.max_length == 255

        payment_field = OnlineOrder._meta.get_field("paymentMethod")
        assert payment_field.max_length == 255


@pytest.mark.django_db
class TestOnlineOrderLineModel:
    """Test cases for the OnlineOrderLine model."""

    def setup_method(self):
        """Setup test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass"
        )
        self.customer = Customer.objects.create(
            customerId="CUST-000001", userId=self.user
        )
        self.order = OnlineOrder.objects.create(
            onlineOrderId=1,
            customerId=self.customer,
            orderDatetime=timezone.now(),
            shippingProvince="Ontario",
            orderStatus="pending",
            paymentMethod="credit_card",
        )
        self.category = Category.objects.create(categoryId=1, name="Electronics")
        self.product = Product.objects.create(
            productSKU="PROD-0000001", productName="Laptop", categoryId=self.category
        )

    def test_create_online_order_line(self):
        """Test creating an online order line."""
        line = OnlineOrderLine.objects.create(
            lineId=1,
            onlineOrderId=self.order,
            productSKU=self.product,
            quantity=2,
            unitPrice=Decimal("999.99"),
            discountApplied=Decimal("0.00"),
            totalAmount=Decimal("1999.98"),
        )
        assert line.lineId == 1
        assert line.onlineOrderId == self.order
        assert line.productSKU == self.product
        assert line.quantity == 2

    def test_online_order_line_db_table(self):
        """Test that OnlineOrderLine model uses correct database table."""
        assert OnlineOrderLine._meta.db_table == "onlineOrderLine"

    def test_online_order_line_primary_key(self):
        """Test that lineId is the primary key."""
        line = OnlineOrderLine.objects.create(
            lineId=1,
            onlineOrderId=self.order,
            productSKU=self.product,
            quantity=2,
            unitPrice=Decimal("999.99"),
            discountApplied=Decimal("0.00"),
            totalAmount=Decimal("1999.98"),
        )
        line2 = OnlineOrderLine.objects.get(pk=1)
        assert line2.lineId == line.lineId

    def test_online_order_line_decimal_fields(self):
        """Test decimal field handling."""
        line = OnlineOrderLine.objects.create(
            lineId=1,
            onlineOrderId=self.order,
            productSKU=self.product,
            quantity=1,
            unitPrice=Decimal("99.99"),
            discountApplied=Decimal("10.00"),
            totalAmount=Decimal("89.99"),
        )
        assert isinstance(line.unitPrice, Decimal)
        assert isinstance(line.discountApplied, Decimal)
        assert isinstance(line.totalAmount, Decimal)

    def test_online_order_line_foreign_keys(self):
        """Test foreign key relationships."""
        line = OnlineOrderLine.objects.create(
            lineId=1,
            onlineOrderId=self.order,
            productSKU=self.product,
            quantity=1,
            unitPrice=Decimal("999.99"),
            discountApplied=Decimal("0.00"),
            totalAmount=Decimal("999.99"),
        )
        assert line.onlineOrderId.onlineOrderId == 1
        assert line.productSKU.productSKU == "PROD-0000001"

    def test_online_order_line_deletion_cascade(self):
        """Test deleting an order cascades to order lines."""
        line = OnlineOrderLine.objects.create(  # noqa F841
            lineId=1,
            onlineOrderId=self.order,
            productSKU=self.product,
            quantity=1,
            unitPrice=Decimal("999.99"),
            discountApplied=Decimal("0.00"),
            totalAmount=Decimal("999.99"),
        )
        self.order.delete()
        assert OnlineOrderLine.objects.filter(lineId=1).exists() is False

    def test_multiple_order_lines_per_order(self):
        """Test creating multiple lines for one order."""
        for i in range(1, 4):
            product = Product.objects.create(
                productName=f"Product {i}", categoryId=self.category
            )
            OnlineOrderLine.objects.create(
                lineId=i,
                onlineOrderId=self.order,
                productSKU=product,
                quantity=i,
                unitPrice=Decimal(f"{100 * i}.00"),
                discountApplied=Decimal("0.00"),
                totalAmount=Decimal(f"{100 * i}.00"),
            )
        assert OnlineOrderLine.objects.filter(onlineOrderId=self.order).count() == 3

    def test_online_order_line_quantity_tracking(self):
        """Test quantity field updates."""
        line = OnlineOrderLine.objects.create(
            lineId=1,
            onlineOrderId=self.order,
            productSKU=self.product,
            quantity=5,
            unitPrice=Decimal("100.00"),
            discountApplied=Decimal("0.00"),
            totalAmount=Decimal("500.00"),
        )
        line.quantity = 3
        line.save()
        updated = OnlineOrderLine.objects.get(lineId=1)
        assert updated.quantity == 3

    def test_online_order_line_product_deletion(self):
        """Test deleting a product cascades to order lines."""
        line = OnlineOrderLine.objects.create(  # noqa F841
            lineId=1,
            onlineOrderId=self.order,
            productSKU=self.product,
            quantity=1,
            unitPrice=Decimal("999.99"),
            discountApplied=Decimal("0.00"),
            totalAmount=Decimal("999.99"),
        )
        self.product.delete()
        assert OnlineOrderLine.objects.filter(lineId=1).exists() is False
