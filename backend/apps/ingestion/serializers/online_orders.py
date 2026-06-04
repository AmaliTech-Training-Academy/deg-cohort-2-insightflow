from rest_framework import serializers

from ..models.online_injection_job import OnlineInjectionJob


class OnlineInjectionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlineInjectionJob
        fields = [
            "id",
            "status",
            "trigger",
            "total_orders",
            "valid_orders",
            "error_orders",
            "pages_fetched",
            "error_report",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
