from apps.ingestion.models.base import IngestionJob
from apps.ingestion.serializers.ingestion_job import IngestionJobSerializer
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated


class IngestionJobListCreateView(generics.ListCreateAPIView):
    queryset = IngestionJob.objects.select_related("created_by").all()
    serializer_class = IngestionJobSerializer
    permission_classes = [IsAuthenticated]


class IngestionJobDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = IngestionJob.objects.select_related("created_by").all()
    serializer_class = IngestionJobSerializer
    permission_classes = [IsAuthenticated]
