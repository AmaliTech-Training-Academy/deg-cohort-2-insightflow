from apps.ingestion.models.pos import POSStagingRecord
from apps.ingestion.serializers.pos import POSStagingRecordSerializer
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated


class POSStagingListCreateView(generics.ListCreateAPIView):
    queryset = POSStagingRecord.objects.select_related("job").all()
    serializer_class = POSStagingRecordSerializer
    permission_classes = [IsAuthenticated]


class POSStagingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = POSStagingRecord.objects.select_related("job").all()
    serializer_class = POSStagingRecordSerializer
    permission_classes = [IsAuthenticated]
