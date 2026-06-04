import logging

from apps.core.exceptions import NotFoundException
from apps.core.pagination import StandardResultsPagination
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models.online_injection_job import OnlineInjectionJob
from ..serializers.online_orders import OnlineInjectionJobSerializer
from ..services.online_orders_service import OnlineOrdersIngestionService
from ..tasks.fetch_online_orders import fetch_online_orders

logger = logging.getLogger(__name__)


class OnlineOrdersTriggerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        service = OnlineOrdersIngestionService()
        job = service.create_job(trigger="manual")
        fetch_online_orders.delay(job.id)
        data = OnlineInjectionJobSerializer(job).data
        data["message"] = (
            f"Ingestion triggered. "
            f"Poll GET /api/ingestion/online-orders/{job.id}/status/ for updates."
        )
        return Response(data, status=status.HTTP_202_ACCEPTED)


class OnlineOrdersJobStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, job_id: int) -> Response:
        try:
            job = OnlineInjectionJob.objects.get(id=job_id)
        except OnlineInjectionJob.DoesNotExist:
            raise NotFoundException(detail=f"OnlineInjectionJob {job_id} not found.")
        return Response(OnlineInjectionJobSerializer(job).data)


class OnlineOrdersJobListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        jobs = OnlineInjectionJob.objects.all()
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(jobs, request)
        serializer = OnlineInjectionJobSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
