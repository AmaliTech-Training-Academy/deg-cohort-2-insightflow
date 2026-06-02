from django.db import models

from .base import AbstractStagingRecord


class POSStagingRecord(AbstractStagingRecord):
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    store_id = models.CharField(max_length=50, blank=True, null=True)
    product_id = models.CharField(max_length=50, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    transaction_date = models.DateField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ingestion_pos_staging"
        ordering = ["-ingested_at"]

    def __str__(self):
        return f"POS {self.transaction_id or self.pk}"
