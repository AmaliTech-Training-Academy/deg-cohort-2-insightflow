from rest_framework import serializers

from apps.ingestion.models.online_orders import OnlineOrderStagingRecord


class OnlineOrderStagingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlineOrderStagingRecord
        fields = "__all__"
        read_only_fields = ("ingested_at",)
