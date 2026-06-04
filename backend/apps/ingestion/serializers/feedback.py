from rest_framework import serializers

from ..models.feedback import FeedbackSurvey
from ..models.feedback_ingestion_job import FeedbackIngestionJob


class FeedbackSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackSurvey
        fields = [
            "responseId",
            "customerId",
            "onlineOrderId",
            "submissionDate",
            "satisfactionScore",
            "npsScore",
            "productRating",
            "deliveryRating",
            "freeTextComments",
        ]


class FeedbackIngestionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackIngestionJob
        fields = [
            "id",
            "status",
            "total_fetched",
            "created_count",
            "skipped_duplicates",
            "errors",
            "error_details",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
