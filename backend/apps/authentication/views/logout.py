import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers import LogoutSerializer

logger = logging.getLogger(__name__)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=LogoutSerializer, responses={200: LogoutSerializer})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            logger.info(
                f"User logged out: {request.user.email}",
                extra={"user_id": request.user.id},
            )
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
