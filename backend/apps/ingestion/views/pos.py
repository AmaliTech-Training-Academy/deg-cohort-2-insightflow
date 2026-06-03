import logging

from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models.pos import POSStagingRecord
from ..serializers.pos import POSStagingRecordSerializer
from ..services.csv_services import POSIngestionService
from ..tasks.process_pos import process_pos_file

logger = logging.getLogger(__name__)
service = POSIngestionService()


class POSStagingListCreateView(ListCreateAPIView):
    """
    GET  /api/ingestion/pos/   — list all POS staging records
    POST /api/ingestion/pos/   — upload a POS CSV file
    """
    serializer_class = POSStagingRecordSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return POSStagingRecord.objects.select_related('job').order_by('-id')

    def create(self, request, *args, **kwargs):
        # if file is in the request → CSV upload
        if 'file' in request.FILES:
            return self._handle_csv_upload(request)
        # otherwise → normal single record POST
        return super().create(request, *args, **kwargs)

    def _handle_csv_upload(self, request):
        file = request.FILES['file']

        # step 1 — validate the file (size, extension, columns)
        result = service.validate_upload(file)
        if not result['ok']:
            return Response(
                {k: v for k, v in result.items() if k != 'ok'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # step 2 — save file to disk, create IngestionJob
        job = service.accept_upload(
            file,
            uploaded_by=request.user.id
        )

        # step 3 — dispatch to Celery, view is done
        process_pos_file.delay(job.id)

        # step 4 — return 202 with job_id for client to poll
        return Response(
            {
                'job_id': job.id,
                'status': job.status,
                'total_rows': job.total_rows,
                'message': (
                    f'File accepted. '
                    f'Poll GET /api/ingestion/{job.id}/status/ for updates.'
                ),
            },
            status=status.HTTP_202_ACCEPTED
        )


class POSStagingDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET    /api/ingestion/pos/<pk>/
    PUT    /api/ingestion/pos/<pk>/
    PATCH  /api/ingestion/pos/<pk>/
    DELETE /api/ingestion/pos/<pk>/
    """
    serializer_class = POSStagingRecordSerializer
    permission_classes = [IsAuthenticated]
    queryset = POSStagingRecord.objects.select_related('job').all()