from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Pipeline, PipelineStatus
from .serializers import PipelineSerializer


class PipelineListCreateView(generics.ListCreateAPIView):
    queryset = Pipeline.objects.select_related("data_source", "created_by").all()
    serializer_class = PipelineSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PipelineDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Pipeline.objects.select_related("data_source", "created_by").all()
    serializer_class = PipelineSerializer
    permission_classes = [IsAuthenticated]


@extend_schema(responses={200: PipelineSerializer})
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def run_pipeline(request, pk):
    try:
        pipeline = Pipeline.objects.get(pk=pk)
    except Pipeline.DoesNotExist:
        return Response(
            {"detail": "Pipeline not found."}, status=status.HTTP_404_NOT_FOUND
        )

    if pipeline.status == PipelineStatus.RUNNING:
        return Response(
            {"detail": "Pipeline is already running."}, status=status.HTTP_409_CONFLICT
        )

    pipeline.status = PipelineStatus.RUNNING
    pipeline.started_at = timezone.now()
    pipeline.error_message = None
    pipeline.save(update_fields=["status", "started_at", "error_message"])

    try:
        # Simulate pipeline execution — replace with real ETL logic
        pipeline.records_processed = 0
        pipeline.status = PipelineStatus.COMPLETED
        pipeline.completed_at = timezone.now()
        pipeline.save(update_fields=["status", "completed_at", "records_processed"])
    except Exception as exc:
        pipeline.status = PipelineStatus.FAILED
        pipeline.error_message = str(exc)
        pipeline.completed_at = timezone.now()
        pipeline.save(update_fields=["status", "error_message", "completed_at"])

    return Response(PipelineSerializer(pipeline).data, status=status.HTTP_200_OK)
