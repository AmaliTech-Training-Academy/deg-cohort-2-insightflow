from rest_framework import serializers

from .models import InsightReport, Pipeline


class PipelineSerializer(serializers.ModelSerializer):
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)
    data_source_name = serializers.CharField(source="data_source.name", read_only=True)

    class Meta:
        model = Pipeline
        fields = (
            "id",
            "name",
            "status",
            "data_source",
            "data_source_name",
            "started_at",
            "completed_at",
            "records_processed",
            "error_message",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {
            "created_by": {"read_only": True},
            "status": {"read_only": True},
            "started_at": {"read_only": True},
            "completed_at": {"read_only": True},
            "records_processed": {"read_only": True},
            "error_message": {"read_only": True},
        }

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class InsightReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsightReport
        fields = ("id", "pipeline", "title", "content", "created_at")
