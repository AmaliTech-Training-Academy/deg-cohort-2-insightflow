from django.urls import path

from .views.ingestion_job import IngestionJobStatusView
from .views.pos import POSStagingListCreateView

urlpatterns = [
    # POS data — list all ingested line items / upload a new CSV
    path("pos/", POSStagingListCreateView.as_view(), name="pos-list-create"),
    # Upload job status — frontend polls this after receiving 202
    path(
        "<int:job_id>/status/",
        IngestionJobStatusView.as_view(),
        name="ingestion-job-status",
    ),
]
