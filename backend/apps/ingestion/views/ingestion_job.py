import logging
from datetime import timedelta

from celery.result import AsyncResult
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardResultsPagination

from ..models.base import InjectionJob
from ..serializers.ingestion_job import InjectionJobSerializer

STALE_THRESHOLD = timedelta(minutes=10)


class InjectionJobListView(APIView):
    """
    GET /api/ingestion/pos/jobs/

    Returns a paginated list of all POS CSV ingestion jobs.
    Secured — requires a valid JWT token.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        jobs = InjectionJob.objects.all()
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(jobs, request)
        serializer = InjectionJobSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

logger = logging.getLogger(__name__)


class IngestionJobStatusView(APIView):
    """
    GET /api/ingestion/<job_id>/status/

    Returns current state of an ingestion job.
    Client polls this after receiving 202 from the upload endpoint.
    404 if job_id does not exist.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Poll ingestion job status",
        description=(
            "Returns the current state of a CSV ingestion job. "
            "Poll this endpoint after receiving a 202 from POST /api/ingestion/pos/. "
            "The error_report field is only present once status is "
            "'completed' or 'failed'."
        ),
        parameters=[
            OpenApiParameter(
                name="job_id",
                location=OpenApiParameter.PATH,
                description="ID of the ingestion job returned by the upload endpoint.",
                required=True,
                type=int,
            )
        ],
        responses={
            200: inline_serializer(
                name="IngestionJobStatus",
                fields={
                    "job_id": drf_serializers.IntegerField(),
                    "status": drf_serializers.ChoiceField(
                        choices=["pending", "running", "completed", "failed"]
                    ),
                    "total_rows": drf_serializers.IntegerField(),
                    "valid_rows": drf_serializers.IntegerField(
                        help_text="Rows successfully inserted into the database."
                    ),
                    "rejected_rows": drf_serializers.IntegerField(
                        help_text=(
                            "Rows that passed CSV validation but were rejected "
                            "at the DB level (unknown store, cashier, or product)."
                        )
                    ),
                    "error_rows": drf_serializers.IntegerField(
                        help_text="Rows that failed CSV format/type validation."
                    ),
                    "created_at": drf_serializers.DateTimeField(),
                    "updated_at": drf_serializers.DateTimeField(),
                    "error_report": drf_serializers.DictField(
                        required=False,
                        help_text=(
                            "Only present when status is 'completed' or 'failed'."
                        ),
                    ),
                },
            ),
            404: inline_serializer(
                name="JobNotFound",
                fields={"detail": drf_serializers.CharField()},
            ),
        },
    )
    def get(self, request, job_id):
        job = get_object_or_404(InjectionJob, id=job_id)

        # Detect worker crashes: RUNNING job whose task is dead or stale
        if job.status == InjectionJob.StatusChoices.RUNNING:
            task_dead = False
            if job.task_id:
                result = AsyncResult(job.task_id)
                task_dead = result.state in ("FAILURE", "REVOKED")
            stale = timezone.now() - job.updated_at > STALE_THRESHOLD
            if task_dead or stale:
                job.status = InjectionJob.StatusChoices.FAILED
                job.error_report = {"fatal_error": "Worker stopped unexpectedly"}
                job.save(update_fields=["status", "error_report"])

        response = {
            "job_id": job.id,
            "status": job.status,
            "total_rows": job.total_rows,
            "valid_rows": job.valid_rows,
            "rejected_rows": job.rejected_rows,
            "error_rows": job.error_rows,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }

        # attach error report only when job is done
        if job.status in [
            InjectionJob.StatusChoices.COMPLETED,
            InjectionJob.StatusChoices.FAILED,
        ]:
            if job.error_report:
                response["error_report"] = job.error_report

        return Response(response)
