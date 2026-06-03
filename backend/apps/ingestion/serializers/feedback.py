from rest_framework import serializers

from ..models.feedback import FeedbackSurvey


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
