from rest_framework import serializers

from ..models.base import InjectionJob


class InjectionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = InjectionJob
        fields = [
            "id",
            "status",
            "total_rows",
            "valid_rows",
            "error_rows",
            "error_report",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
