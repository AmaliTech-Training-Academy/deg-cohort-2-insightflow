from django.urls import path

from apps.ingestion.views.feedback import (
    FeedbackStagingDetailView,
    FeedbackStagingListCreateView,
)
from apps.ingestion.views.ingestion_job import (
    IngestionJobDetailView,
    IngestionJobListCreateView,
)
from apps.ingestion.views.inventory import (
    InventoryStagingDetailView,
    InventoryStagingListCreateView,
)
from apps.ingestion.views.online_orders import (
    OnlineOrderStagingDetailView,
    OnlineOrderStagingListCreateView,
)
from apps.ingestion.views.pos import POSStagingDetailView, POSStagingListCreateView

urlpatterns = [
    path("jobs/", IngestionJobListCreateView.as_view(), name="ingestion-job-list"),
    path("jobs/<int:pk>/", IngestionJobDetailView.as_view(), name="ingestion-job-detail"),
    path("pos/", POSStagingListCreateView.as_view(), name="ingestion-pos-list"),
    path("pos/<int:pk>/", POSStagingDetailView.as_view(), name="ingestion-pos-detail"),
    path(
        "online-orders/",
        OnlineOrderStagingListCreateView.as_view(),
        name="ingestion-online-orders-list",
    ),
    path(
        "online-orders/<int:pk>/",
        OnlineOrderStagingDetailView.as_view(),
        name="ingestion-online-orders-detail",
    ),
    path(
        "feedback/",
        FeedbackStagingListCreateView.as_view(),
        name="ingestion-feedback-list",
    ),
    path(
        "feedback/<int:pk>/",
        FeedbackStagingDetailView.as_view(),
        name="ingestion-feedback-detail",
    ),
    path(
        "inventory/",
        InventoryStagingListCreateView.as_view(),
        name="ingestion-inventory-list",
    ),
    path(
        "inventory/<int:pk>/",
        InventoryStagingDetailView.as_view(),
        name="ingestion-inventory-detail",
    ),
]
