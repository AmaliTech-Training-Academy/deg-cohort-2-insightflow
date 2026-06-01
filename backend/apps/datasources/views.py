from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import DataSource
from .serializers import DataSourceSerializer


class DataSourceListCreateView(generics.ListCreateAPIView):
    queryset = DataSource.objects.select_related("created_by").all()
    serializer_class = DataSourceSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DataSourceDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DataSource.objects.select_related("created_by").all()
    serializer_class = DataSourceSerializer
    permission_classes = [IsAuthenticated]
