from apps.ingestion.models.inventory import InventoryStagingRecord
from rest_framework import serializers


class InventoryStagingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryStagingRecord
        fields = "__all__"
        read_only_fields = ("ingested_at",)
