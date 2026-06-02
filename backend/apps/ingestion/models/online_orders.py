from apps.ingestion.models.base import Customer
from apps.ingestion.models.inventory import Product
from django.db import models


class OnlineOrder(models.Model):
    onlineOrderId = models.IntegerField(primary_key=True, db_column="onlineOrderId")
    customerId = models.ForeignKey(
        Customer, on_delete=models.CASCADE, db_column="customerId"
    )
    orderDatetime = models.DateTimeField(db_column="orderDatetime")
    shippingProvince = models.CharField(max_length=255, db_column="shippingProvince")
    orderStatus = models.CharField(max_length=255, db_column="orderStatus")
    paymentMethod = models.CharField(max_length=255, db_column="paymentMethod")

    class Meta:
        db_table = "onlineOrder"


class OnlineOrderLine(models.Model):
    lineId = models.IntegerField(primary_key=True, db_column="lineId")
    onlineOrderId = models.ForeignKey(
        OnlineOrder, on_delete=models.CASCADE, db_column="onlineOrderId"
    )
    productSKU = models.ForeignKey(
        Product, on_delete=models.CASCADE, to_field="productSKU", db_column="productSKU"
    )
    quantity = models.IntegerField(db_column="quantity")
    unitPrice = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="unitPrice"
    )
    discountApplied = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="discountApplied"
    )
    totalAmount = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="totalAmount"
    )

    class Meta:
        db_table = "onlineOrderLine"
