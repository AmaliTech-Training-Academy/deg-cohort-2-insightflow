"""
Tests for the FeedbackSurvey model.
"""
import pytest
from datetime import date
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.ingestion.models.base import Customer
from apps.ingestion.models.inventory import Category, Product
from apps.ingestion.models.online_orders import OnlineOrder
from apps.ingestion.models.feedback import FeedbackSurvey

User = get_user_model()


@pytest.mark.django_db
class TestFeedbackSurveyModel:
    """Test cases for the FeedbackSurvey model."""

    def setup_method(self):
        """Setup test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="pass"
        )
        self.customer = Customer.objects.create(customerId="CUST-000001", userId=self.user)
        self.order = OnlineOrder.objects.create(
            onlineOrderId=1,
            customerId=self.customer,
            orderDatetime=timezone.now(),
            shippingProvince="Ontario",
            orderStatus="completed",
            paymentMethod="credit_card",
        )

    def test_create_feedback_survey(self):
        """Test creating a feedback survey."""
        survey = FeedbackSurvey.objects.create(
            responseId=1,
            customerId=self.customer,
            onlineOrderId=self.order,
            submissionDate=date.today(),
            satisfactionScore=5,
            npsScore=9,
            productRating=4,
            deliveryRating=5,
            freeTextComments="Great product and fast delivery!",
        )
        assert survey.responseId == 1
        assert survey.customerId == self.customer
        assert survey.onlineOrderId == self.order
        assert survey.satisfactionScore == 5
        assert survey.npsScore == 9

    def test_feedback_survey_db_table(self):
        """Test that FeedbackSurvey model uses correct database table."""
        assert FeedbackSurvey._meta.db_table == "feedbackSurvey"

    def test_feedback_survey_primary_key(self):
        """Test that responseId is the primary key."""
        survey = FeedbackSurvey.objects.create(
            responseId=1,
            customerId=self.customer,
            onlineOrderId=self.order,
            submissionDate=date.today(),
            satisfactionScore=5,
            npsScore=9,
            productRating=4,
            deliveryRating=5,
            freeTextComments="Test",
        )
        survey2 = FeedbackSurvey.objects.get(pk=1)
        assert survey2.responseId == survey.responseId

    def test_feedback_survey_without_order(self):
        """Test creating feedback survey without linking to an order."""
        survey = FeedbackSurvey.objects.create(
            responseId=1,
            customerId=self.customer,
            submissionDate=date.today(),
            satisfactionScore=5,
            npsScore=9,
            productRating=4,
            deliveryRating=5,
            freeTextComments="Feedback without order",
        )
        assert survey.onlineOrderId is None

    def test_feedback_survey_foreign_keys(self):
        """Test feedback survey foreign key relationships."""
        survey = FeedbackSurvey.objects.create(
            responseId=1,
            customerId=self.customer,
            onlineOrderId=self.order,
            submissionDate=date.today(),
            satisfactionScore=5,
            npsScore=9,
            productRating=4,
            deliveryRating=5,
            freeTextComments="Test",
        )
        assert survey.customerId.customerId == "CUST-000001"
        assert survey.onlineOrderId.onlineOrderId == 1

    def test_feedback_survey_satisfaction_score_range(self):
        """Test satisfaction score values."""
        for score in range(1, 6):
            survey = FeedbackSurvey.objects.create(
                responseId=score,
                customerId=self.customer,
                submissionDate=date.today(),
                satisfactionScore=score,
                npsScore=8,
                productRating=4,
                deliveryRating=4,
                freeTextComments="Test",
            )
            assert survey.satisfactionScore == score

    def test_feedback_survey_nps_score_range(self):
        """Test NPS score values."""
        for score in [0, 5, 10]:
            survey = FeedbackSurvey.objects.create(
                responseId=score,
                customerId=self.customer,
                submissionDate=date.today(),
                satisfactionScore=5,
                npsScore=score,
                productRating=4,
                deliveryRating=4,
                freeTextComments="Test",
            )
            assert survey.npsScore == score

    def test_feedback_survey_product_rating(self):
        """Test product rating values."""
        for rating in range(1, 6):
            survey = FeedbackSurvey.objects.create(
                responseId=rating + 100,
                customerId=self.customer,
                submissionDate=date.today(),
                satisfactionScore=5,
                npsScore=8,
                productRating=rating,
                deliveryRating=4,
                freeTextComments="Test",
            )
            assert survey.productRating == rating

    def test_feedback_survey_delivery_rating(self):
        """Test delivery rating values."""
        for rating in range(1, 6):
            survey = FeedbackSurvey.objects.create(
                responseId=rating + 200,
                customerId=self.customer,
                submissionDate=date.today(),
                satisfactionScore=5,
                npsScore=8,
                productRating=4,
                deliveryRating=rating,
                freeTextComments="Test",
            )
            assert survey.deliveryRating == rating

    def test_feedback_survey_free_text_comments(self):
        """Test free text comments field."""
        comments = "This is a detailed review. The product quality is excellent!"
        survey = FeedbackSurvey.objects.create(
            responseId=1,
            customerId=self.customer,
            submissionDate=date.today(),
            satisfactionScore=5,
            npsScore=10,
            productRating=5,
            deliveryRating=5,
            freeTextComments=comments,
        )
        assert survey.freeTextComments == comments

    def test_feedback_survey_empty_comments(self):
        """Test feedback survey with empty comments."""
        survey = FeedbackSurvey.objects.create(
            responseId=1,
            customerId=self.customer,
            submissionDate=date.today(),
            satisfactionScore=5,
            npsScore=9,
            productRating=4,
            deliveryRating=5,
            freeTextComments="",
        )
        assert survey.freeTextComments == ""

    def test_feedback_survey_deletion_cascade_on_customer(self):
        """Test deleting a customer cascades to feedback surveys."""
        survey = FeedbackSurvey.objects.create(
            responseId=1,
            customerId=self.customer,
            onlineOrderId=self.order,
            submissionDate=date.today(),
            satisfactionScore=5,
            npsScore=9,
            productRating=4,
            deliveryRating=5,
            freeTextComments="Test",
        )
        self.customer.delete()
        assert FeedbackSurvey.objects.filter(responseId=1).exists() is False

    def test_feedback_survey_set_null_on_order_delete(self):
        """Test that deleting order sets onlineOrderId to NULL."""
        survey = FeedbackSurvey.objects.create(
            responseId=1,
            customerId=self.customer,
            onlineOrderId=self.order,
            submissionDate=date.today(),
            satisfactionScore=5,
            npsScore=9,
            productRating=4,
            deliveryRating=5,
            freeTextComments="Test",
        )
        self.order.delete()
        survey.refresh_from_db()
        assert survey.onlineOrderId is None

    def test_multiple_surveys_same_customer(self):
        """Test creating multiple surveys for same customer."""
        for i in range(1, 4):
            FeedbackSurvey.objects.create(
                responseId=i,
                customerId=self.customer,
                submissionDate=date.today(),
                satisfactionScore=5,
                npsScore=9,
                productRating=4,
                deliveryRating=5,
                freeTextComments=f"Survey {i}",
            )
        assert FeedbackSurvey.objects.filter(customerId=self.customer).count() == 3

    def test_feedback_survey_submission_date_tracking(self):
        """Test submission date tracking."""
        today = date.today()
        survey = FeedbackSurvey.objects.create(
            responseId=1,
            customerId=self.customer,
            submissionDate=today,
            satisfactionScore=5,
            npsScore=9,
            productRating=4,
            deliveryRating=5,
            freeTextComments="Test",
        )
        assert survey.submissionDate == today

    def test_feedback_survey_update(self):
        """Test updating a feedback survey."""
        survey = FeedbackSurvey.objects.create(
            responseId=1,
            customerId=self.customer,
            submissionDate=date.today(),
            satisfactionScore=3,
            npsScore=6,
            productRating=2,
            deliveryRating=3,
            freeTextComments="Not satisfied",
        )
        survey.satisfactionScore = 5
        survey.npsScore = 9
        survey.productRating = 4
        survey.deliveryRating = 5
        survey.freeTextComments = "Much better!"
        survey.save()

        updated = FeedbackSurvey.objects.get(responseId=1)
        assert updated.satisfactionScore == 5
        assert updated.npsScore == 9
        assert updated.productRating == 4
        assert updated.deliveryRating == 5
