from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models.feedback_ingestion_job import FeedbackIngestionJob
from ..serializers.feedback import FeedbackIngestionJobSerializer
from ..tasks.ingest_feedback import ingest_feedback


class FeedbackIngestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        job = FeedbackIngestionJob.objects.create()
        ingest_feedback.delay(job.id)
        return Response(
            {
                "job_id": job.id,
                "status": job.status,
                "message": "Feedback ingestion triggered.",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class FeedbackJobStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, job_id: int) -> Response:
        try:
            job = FeedbackIngestionJob.objects.get(pk=job_id)
        except FeedbackIngestionJob.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(FeedbackIngestionJobSerializer(job).data)


class FeedbackJobListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        jobs = FeedbackIngestionJob.objects.all()
        return Response(FeedbackIngestionJobSerializer(jobs, many=True).data)
