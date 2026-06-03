from apps.authentication.models import User
from apps.ingestion.models.inventory import Product, Store
from django.db import models


class Cashier(models.Model):
    cashierId = models.IntegerField(primary_key=True, db_column="cashierId")
    storeId = models.ForeignKey(Store, on_delete=models.CASCADE, db_column="storeId")
    fullName = models.CharField(max_length=255, db_column="fullName")
    userId = models.ForeignKey(User, on_delete=models.CASCADE, db_column="userId")

    class Meta:
        db_table = "cashier"


class PosTransaction(models.Model):
    posTransactionId = models.IntegerField(
        primary_key=True, db_column="posTransactionId"
    )
    storeId = models.ForeignKey(Store, on_delete=models.CASCADE, db_column="storeId")
    cashierId = models.ForeignKey(
        Cashier, on_delete=models.CASCADE, db_column="cashierId"
    )
    transactionDatetime = models.DateTimeField(db_column="transactionDatetime")

    class Meta:
        db_table = "posTransaction"


class PosTransactionLine(models.Model):
    lineId = models.IntegerField(primary_key=True, db_column="lineId")
    posTransactionId = models.ForeignKey(
        PosTransaction, on_delete=models.CASCADE, db_column="posTransactionId"
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
        db_table = "posTransactionLine"
