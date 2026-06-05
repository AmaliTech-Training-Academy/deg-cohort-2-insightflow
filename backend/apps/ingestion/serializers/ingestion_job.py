from rest_framework import serializers

from ..models.base import InjectionJob


class InjectionJobSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()

    def get_file_name(self, obj: InjectionJob) -> str:
        if obj.file and obj.file.name:
            return str(obj.file.name).split("/")[-1]
        return f"job-{obj.id}"

    class Meta:
        model = InjectionJob
        fields = [
            "id",
            "file_name",
            "status",
            "total_rows",
            "valid_rows",
            "rejected_rows",
            "error_rows",
            "error_report",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
