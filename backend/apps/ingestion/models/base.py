from django.conf import settings
from django.db import models


class IngestionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class IngestionJob(models.Model):
    class SourceType(models.TextChoices):
        POS = "POS", "Point of Sale"
        ONLINE_ORDERS = "ONLINE_ORDERS", "Online Orders"
        FEEDBACK = "FEEDBACK", "Customer Feedback"
        INVENTORY = "INVENTORY", "Inventory"

    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    status = models.CharField(
        max_length=20,
        choices=IngestionStatus.choices,
        default=IngestionStatus.PENDING,
    )
    file_path = models.CharField(max_length=500, blank=True, null=True)
    connection_url = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="ingestion_jobs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ingestion_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.source_type} job #{self.pk} [{self.status}]"


class AbstractStagingRecord(models.Model):
    """Abstract base for all per-source staging tables."""

    job = models.ForeignKey(
        IngestionJob,
        on_delete=models.CASCADE,
        related_name="%(class)s_records",
    )
    status = models.CharField(
        max_length=20,
        choices=IngestionStatus.choices,
        default=IngestionStatus.PENDING,
    )
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    ingested_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
