import logging

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models.base import IngestionJob

logger = logging.getLogger(__name__)


class IngestionJobStatusView(APIView):
    """
    GET /api/ingestion/<job_id>/status/

    Returns current state of an ingestion job.
    Client polls this after receiving 202 from the upload endpoint.
    404 if job_id does not exist.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        job = get_object_or_404(IngestionJob, id=job_id)

        response = {
            'job_id':     job.id,
            'status':     job.status,
            'total_rows': job.total_rows,
            'valid_rows': job.valid_rows,
            'error_rows': job.error_rows,
            'created_at': job.created_at,
            'updated_at': job.updated_at,
        }

        # attach error report only when job is done
        if job.status in [
            IngestionJob.STATUS_COMPLETED,
            IngestionJob.STATUS_FAILED
        ]:
            if job.error_report:
                response['error_report'] = job.error_report

        return Response(response)