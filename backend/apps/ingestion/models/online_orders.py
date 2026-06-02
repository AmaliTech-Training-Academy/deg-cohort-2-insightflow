from django.db import models

from .base import AbstractStagingRecord


class OnlineOrderStagingRecord(AbstractStagingRecord):
    order_id = models.CharField(max_length=100, blank=True, null=True)
    customer_id = models.CharField(max_length=50, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    items = models.JSONField(default=list, blank=True)
    order_date = models.DateField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ingestion_online_orders_staging"
        ordering = ["-ingested_at"]

    def __str__(self):
        return f"OnlineOrder {self.order_id or self.pk}"
