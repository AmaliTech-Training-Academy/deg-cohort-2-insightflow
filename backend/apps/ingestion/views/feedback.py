from apps.ingestion.models.feedback import FeedbackStagingRecord
from apps.ingestion.serializers.feedback import FeedbackStagingRecordSerializer
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated


class FeedbackStagingListCreateView(generics.ListCreateAPIView):
    queryset = FeedbackStagingRecord.objects.select_related("job").all()
    serializer_class = FeedbackStagingRecordSerializer
    permission_classes = [IsAuthenticated]


class FeedbackStagingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FeedbackStagingRecord.objects.select_related("job").all()
    serializer_class = FeedbackStagingRecordSerializer
    permission_classes = [IsAuthenticated]
