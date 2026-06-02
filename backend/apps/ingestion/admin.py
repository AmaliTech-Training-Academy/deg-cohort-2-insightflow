from django.contrib import admin

from apps.ingestion.models.base import IngestionJob
from apps.ingestion.models.feedback import FeedbackStagingRecord
from apps.ingestion.models.inventory import InventoryStagingRecord
from apps.ingestion.models.online_orders import OnlineOrderStagingRecord
from apps.ingestion.models.pos import POSStagingRecord


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = ("source_type", "status", "created_by", "created_at")
    list_filter = ("source_type", "status")
    search_fields = ("source_type",)


@admin.register(POSStagingRecord)
class POSStagingAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "store_id", "amount", "transaction_date", "status")
    list_filter = ("status",)


@admin.register(OnlineOrderStagingRecord)
class OnlineOrderStagingAdmin(admin.ModelAdmin):
    list_display = ("order_id", "customer_id", "amount", "order_date", "status")
    list_filter = ("status",)


@admin.register(FeedbackStagingRecord)
class FeedbackStagingAdmin(admin.ModelAdmin):
    list_display = ("feedback_id", "customer_id", "rating", "feedback_date", "status")
    list_filter = ("status",)


@admin.register(InventoryStagingRecord)
class InventoryStagingAdmin(admin.ModelAdmin):
    list_display = ("product_id", "warehouse_id", "quantity", "snapshot_date", "status")
    list_filter = ("status",)
