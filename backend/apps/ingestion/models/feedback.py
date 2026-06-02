from django.db import models
from django.contrib.auth.models import AbstractUser

from apps.ingestion.models.base import Customer
from apps.ingestion.models.online_orders import OnlineOrder


class FeedbackSurvey(models.Model):
    responseId = models.IntegerField(primary_key=True, db_column="responseId")
    customerId = models.ForeignKey(
        Customer, on_delete=models.CASCADE, db_column="customerId"
    )
    onlineOrderId = models.ForeignKey(
        OnlineOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="onlineOrderId",
    )
    submissionDate = models.DateField(db_column="submissionDate")
    satisfactionScore = models.PositiveSmallIntegerField(db_column="satisfactionScore")
    npsScore = models.PositiveSmallIntegerField(db_column="npsScore")
    productRating = models.PositiveSmallIntegerField(db_column="productRating")
    deliveryRating = models.PositiveSmallIntegerField(db_column="deliveryRating")
    freeTextComments = models.TextField(db_column="freeTextComments")

    class Meta:
        db_table = "feedbackSurvey"
