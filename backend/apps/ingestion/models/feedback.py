from django.db import models

from .base import AbstractStagingRecord


class FeedbackStagingRecord(AbstractStagingRecord):
    feedback_id = models.CharField(max_length=100, blank=True, null=True)
    customer_id = models.CharField(max_length=50, blank=True, null=True)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)
    feedback_date = models.DateField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ingestion_feedback_staging"
        ordering = ["-ingested_at"]

    def __str__(self):
        return f"Feedback {self.feedback_id or self.pk}"
