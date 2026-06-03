from django.urls import path

from .views.ingestion_job import IngestionJobStatusView
from .views.pos import POSStagingDetailView, POSStagingListCreateView

urlpatterns = [
    # POS data — list all ingested line items / upload a new CSV
    path("pos/", POSStagingListCreateView.as_view(), name="pos-list-create"),
    # POS data — retrieve / update / delete a single line item
    path("pos/<int:pk>/", POSStagingDetailView.as_view(), name="pos-detail"),
    # Upload job status — frontend polls this after receiving 202
    path(
        "<int:job_id>/status/",
        IngestionJobStatusView.as_view(),
        name="ingestion-job-status",
    ),
]
