from rest_framework import serializers

from .models import DataSource


class DataSourceSerializer(serializers.ModelSerializer):
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model = DataSource
        fields = (
            "id",
            "name",
            "type",
            "connection_url",
            "file_path",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {"created_by": {"read_only": True}}

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)
