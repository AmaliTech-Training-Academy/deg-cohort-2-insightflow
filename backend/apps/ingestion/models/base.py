from typing import Any

from apps.authentication.models import User
from django.db import models


class Customer(models.Model):
    customerId = models.CharField(
        max_length=20, primary_key=True, db_column="customerId"
    )
    userId = models.ForeignKey(User, on_delete=models.CASCADE, db_column="userId")

    class Meta:
        db_table = "customer"

    def save(self, *args, **kwargs):
        if not self.customerId:
            last_customer = Customer.objects.all().order_by("customerId").last()
            if not last_customer:
                self.customerId = "CUST-000001"
            else:
                last_number = int(last_customer.customerId.split("-")[1])
                next_number = last_number + 1
                self.customerId = f"CUST-{next_number:06d}"
        super().save(*args, **kwargs)


class InjectionJob(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id: int  # explicit annotation so Pylance can resolve the auto-generated PK
    file = models.FileField(upload_to="uploads/pos_csv/%Y/%m/%d/")
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    total_rows = models.IntegerField(
        null=True, blank=True, help_text="Total rows counted before processing"
    )
    valid_rows = models.IntegerField(default=0)
    error_rows = models.IntegerField(default=0)
    error_report: dict[str, Any] | None = models.JSONField(  # type: ignore[assignment]
        null=True, blank=True, help_text="Detailed error logs filled after processing"
    )
    task_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "POS Upload"
        verbose_name_plural = "POS Uploads"

    def __str__(self):
        return f"File {self.id} - {self.status}"
