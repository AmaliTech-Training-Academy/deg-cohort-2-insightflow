from django.urls import path

from .views.feedback import (
    FeedbackIngestView,
    FeedbackJobListView,
    FeedbackJobStatusView,
)
from .views.ingestion_job import IngestionJobListView, IngestionJobStatusView
from .views.online_orders import (
    OnlineOrdersJobListView,
    OnlineOrdersJobStatusView,
    OnlineOrdersTriggerView,
)
from .views.pos import POSStagingListCreateView

urlpatterns = [
    path("pos/", POSStagingListCreateView.as_view(), name="pos-list-create"),
    path("pos/jobs/", IngestionJobListView.as_view(), name="pos-job-list"),
    path("feedback/trigger/", FeedbackIngestView.as_view(), name="feedback-trigger"),
    path("feedback/jobs/", FeedbackJobListView.as_view(), name="feedback-job-list"),
    path(
        "feedback/jobs/<int:job_id>/status/",
        FeedbackJobStatusView.as_view(),
        name="feedback-job-status",
    ),
    path(
        "<int:job_id>/status/",
        IngestionJobStatusView.as_view(),
        name="ingestion-job-status",
    ),
    path(
        "online-orders/trigger/",
        OnlineOrdersTriggerView.as_view(),
        name="online-orders-trigger",
    ),
    path(
        "online-orders/jobs/",
        OnlineOrdersJobListView.as_view(),
        name="online-orders-job-list",
    ),
    path(
        "online-orders/<int:job_id>/status/",
        OnlineOrdersJobStatusView.as_view(),
        name="online-orders-job-status",
    ),
]
