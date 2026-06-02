from apps.ingestion.models.base import IngestionJob
from rest_framework import serializers


class IngestionJobSerializer(serializers.ModelSerializer):
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model = IngestionJob
        fields = "__all__"
        read_only_fields = ("status", "created_by", "created_at", "updated_at")

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)
