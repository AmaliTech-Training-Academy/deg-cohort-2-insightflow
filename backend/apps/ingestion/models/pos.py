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


class InjectionJob(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    file = models.FileField(upload_to="uploads/pos_csv/%Y/%m/%d/")
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    total_rows = models.IntegerField(
        null=True, blank=True, help_text="Total rows counted before processing"
    )
    valid_rows = models.IntegerField(default=0)
    error_rows = models.IntegerField(default=0)
    error_report = models.JSONField(
        null=True, blank=True, help_text="Detailed error logs filled after processing"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "POS Upload"
        verbose_name_plural = "POS Uploads"

    def __str__(self):
        return f"File {self.id} - {self.status}"
