from apps.ingestion.models.pos import POSStagingRecord
from rest_framework import serializers


class POSStagingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = POSStagingRecord
        fields = "__all__"
        read_only_fields = ("ingested_at",)
