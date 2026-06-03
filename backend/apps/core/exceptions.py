import logging

from rest_framework import status
from rest_framework.exceptions import APIException as DRFAPIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class AppException(DRFAPIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code = "api_error"
    default_detail = "An unexpected error occurred."


class ValidationException(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "validation_error"
    default_detail = "Validation failed."

    def __init__(self, detail=None, code=None, details=None):
        super().__init__(detail, code)
        self.details = details or {}


class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "not_found"
    default_detail = "Resource not found."


class UnauthorizedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "unauthorized"
    default_detail = "Authentication required."


class ForbiddenException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "forbidden"
    default_detail = "Permission denied."


class ConflictException(AppException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"
    default_detail = "Resource conflict."


class RateLimitException(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "rate_limit_exceeded"
    default_detail = "Rate limit exceeded."


class InternalServerException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code = "internal_error"
    default_detail = "Internal server error."


def custom_exception_handler(exc, context):
    """Custom exception handler for API responses."""
    response = exception_handler(exc, context)

    if response is None:
        logger.error(
            f"Unhandled exception: {str(exc)}",
            exc_info=True,
            extra={"exception": type(exc).__name__},
        )
        return Response(
            {
                "error": True,
                "message": "An unexpected error occurred.",
                "code": "internal_error",
                "details": {},
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, AppException):
        message = str(exc.detail)
        error_code = exc.default_code
        extra_details = getattr(exc, "details", {})
    elif isinstance(response.data, dict) and "detail" in response.data:
        message = str(response.data["detail"])
        error_code = "api_error"
        extra_details = {}
    elif isinstance(response.data, dict):
        message = "Validation failed."
        error_code = "validation_error"
        extra_details = response.data
    else:
        message = str(response.data)
        error_code = "api_error"
        extra_details = {}

    response.data = {
        "error": True,
        "message": message,
        "code": error_code,
        "details": extra_details,
    }

    logger.warning(
        f"API Error: {message}",
        extra={
            "status_code": response.status_code,
            "error_code": error_code,
            "path": context.get("request").path if context.get("request") else None,
        },
    )

    return response
