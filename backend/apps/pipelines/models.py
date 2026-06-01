from apps.datasources.models import DataSource
from django.conf import settings
from django.db import models


class PipelineStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class Pipeline(models.Model):
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=PipelineStatus.choices, default=PipelineStatus.PENDING
    )
    data_source = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, related_name="pipelines"
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    records_processed = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pipelines",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pipelines"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} [{self.status}]"


class InsightReport(models.Model):
    pipeline = models.ForeignKey(
        Pipeline, on_delete=models.CASCADE, related_name="reports"
    )
    title = models.CharField(max_length=255)
    content = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "insight_reports"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
