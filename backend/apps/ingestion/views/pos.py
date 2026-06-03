import logging

from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from ..models.pos import PosTransactionLine
from ..serializers.pos import PosTransactionLineSerializer
from ..services.csv_services import POSIngestionService
from ..tasks.process_pos import process_pos_file


class POSUploadThrottle(UserRateThrottle):
    """Limits CSV uploads to 20 per hour per authenticated user."""

    scope = "pos_upload"


logger = logging.getLogger(__name__)
service = POSIngestionService()


@extend_schema_view(
    list=extend_schema(
        summary="List POS staging records",
        description="Returns all POS transaction line records in the staging area.",
    ),
    create=extend_schema(
        summary="Upload POS CSV file",
        description=(
            "Upload a POS CSV file (max 50MB). "
            "Required columns: transaction_id, date, store_id, product_sku, "
            "quantity, unit_price, total. "
            "Returns a job_id — poll GET /api/ingestion/{job_id}/status/ for progress."
        ),
        request={
            "multipart/form-data": inline_serializer(
                name="POSCSVUpload",
                fields={"file": drf_serializers.FileField()},
            )
        },
        responses={
            202: inline_serializer(
                name="POSUploadAccepted",
                fields={
                    "job_id": drf_serializers.IntegerField(),
                    "status": drf_serializers.CharField(),
                    "total_rows": drf_serializers.IntegerField(),
                    "message": drf_serializers.CharField(),
                },
            ),
            400: inline_serializer(
                name="POSUploadError",
                fields={
                    "error": drf_serializers.CharField(),
                    "details": drf_serializers.DictField(required=False),
                },
            ),
        },
    ),
)
class POSStagingListCreateView(ListCreateAPIView):
    """
    GET  /api/ingestion/pos/   — list all POS staging records
    POST /api/ingestion/pos/   — upload a POS CSV file
    """

    serializer_class = PosTransactionLineSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_throttles(self):
        # Apply upload throttle only on POST (CSV upload), not on GET
        if self.request.method == "POST":
            return [POSUploadThrottle()]
        return []

    def get_queryset(self):
        return PosTransactionLine.objects.select_related(
            "posTransactionId", "productSKU"
        ).order_by("-lineId")

    def create(self, request, *args, **kwargs):
        # if file is in the request → CSV upload
        if "file" in request.FILES:
            return self._handle_csv_upload(request)
        # otherwise → normal single record POST
        return super().create(request, *args, **kwargs)

    def _handle_csv_upload(self, request):
        file = request.FILES["file"]

        # step 1 — validate (raises FileSizeLimitException,
        #           UnsupportedFileTypeException, CSVParseException, or
        #           ValidationException on failure; the custom exception handler
        #           converts them to the appropriate 4xx response automatically)
        service.validate_upload(file)

        # step 2 — save file to disk, create IngestionJob
        job = service.accept_upload(file, uploaded_by=request.user.id)

        # step 3 — dispatch to Celery, store task_id for state tracking
        task = process_pos_file.delay(job.id)
        job.task_id = task.id
        job.save(update_fields=["task_id"])

        # step 4 — return 202 with job_id for client to poll
        return Response(
            {
                "job_id": job.id,
                "status": job.status,
                "total_rows": job.total_rows,
                "message": (
                    f"File accepted. "
                    f"Poll GET /api/ingestion/{job.id}/status/ for updates."
                ),
            },
            status=status.HTTP_202_ACCEPTED,
        )
