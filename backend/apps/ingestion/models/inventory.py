from django.db import models

from .base import AbstractStagingRecord


class InventoryStagingRecord(AbstractStagingRecord):
    product_id = models.CharField(max_length=50, blank=True, null=True)
    warehouse_id = models.CharField(max_length=50, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=0)
    snapshot_date = models.DateField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ingestion_inventory_staging"
        ordering = ["-ingested_at"]

    def __str__(self):
        return f"Inventory {self.product_id or self.pk}"
