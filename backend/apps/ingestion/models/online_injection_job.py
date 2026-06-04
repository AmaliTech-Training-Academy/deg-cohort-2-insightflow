from typing import Any

from django.db import models


class OnlineInjectionJob(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class TriggerChoices(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        MANUAL = "manual", "Manual"

    id: int
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    trigger = models.CharField(
        max_length=20, choices=TriggerChoices.choices, default=TriggerChoices.SCHEDULED
    )
    total_orders = models.IntegerField(null=True, blank=True)
    valid_orders = models.IntegerField(default=0)
    error_orders = models.IntegerField(default=0)
    pages_fetched = models.IntegerField(default=0)
    error_report: dict[str, Any] | None = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "online_injection_job"
        ordering = ["-created_at"]
        verbose_name = "Online Orders Ingestion Job"
        verbose_name_plural = "Online Orders Ingestion Jobs"

    def __str__(self) -> str:
        return f"OnlineInjectionJob {self.id} - {self.status}"
