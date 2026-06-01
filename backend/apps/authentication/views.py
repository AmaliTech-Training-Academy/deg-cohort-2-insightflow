from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


@extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    tokens = _tokens_for_user(user)
    return Response(
        {"user": UserSerializer(user).data, "token": tokens["access"]},
        status=status.HTTP_201_CREATED,
    )


@extend_schema(request=LoginSerializer)
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    tokens = _tokens_for_user(user)
    return Response(
        {"user": UserSerializer(user).data, "token": tokens["access"]},
        status=status.HTTP_200_OK,
    )
