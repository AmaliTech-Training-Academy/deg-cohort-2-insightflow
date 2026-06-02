from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.ingestion.models.inventory import InventoryStagingRecord
from apps.ingestion.serializers.inventory import InventoryStagingRecordSerializer


class InventoryStagingListCreateView(generics.ListCreateAPIView):
    queryset = InventoryStagingRecord.objects.select_related("job").all()
    serializer_class = InventoryStagingRecordSerializer
    permission_classes = [IsAuthenticated]


class InventoryStagingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = InventoryStagingRecord.objects.select_related("job").all()
    serializer_class = InventoryStagingRecordSerializer
    permission_classes = [IsAuthenticated]
