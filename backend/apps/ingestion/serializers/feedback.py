from apps.ingestion.models.feedback import FeedbackStagingRecord
from rest_framework import serializers


class FeedbackStagingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackStagingRecord
        fields = "__all__"
        read_only_fields = ("ingested_at",)
