from django.db import models


class FeedbackIngestionJob(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    total_fetched = models.IntegerField(default=0)
    created_count = models.IntegerField(default=0)
    skipped_duplicates = models.IntegerField(default=0)
    errors = models.IntegerField(default=0)
    error_details = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "feedback_ingestion_job"
        ordering = ["-created_at"]
        verbose_name = "Feedback Ingestion Job"
        verbose_name_plural = "Feedback Ingestion Jobs"

    def __str__(self) -> str:
        return f"FeedbackIngestionJob {self.id} - {self.status}"
