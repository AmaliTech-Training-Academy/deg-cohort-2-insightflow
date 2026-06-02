from apps.ingestion.models.online_orders import OnlineOrderStagingRecord
from apps.ingestion.serializers.online_orders import OnlineOrderStagingRecordSerializer
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated


class OnlineOrderStagingListCreateView(generics.ListCreateAPIView):
    queryset = OnlineOrderStagingRecord.objects.select_related("job").all()
    serializer_class = OnlineOrderStagingRecordSerializer
    permission_classes = [IsAuthenticated]


class OnlineOrderStagingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OnlineOrderStagingRecord.objects.select_related("job").all()
    serializer_class = OnlineOrderStagingRecordSerializer
    permission_classes = [IsAuthenticated]
