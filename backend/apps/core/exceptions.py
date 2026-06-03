import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class APIException(Exception):
    """Base exception for API errors."""

    def __init__(self, message, code=None, status_code=None):
        self.message = message
        self.code = code or "api_error"
        self.status_code = status_code or status.HTTP_500_INTERNAL_SERVER_ERROR
        super().__init__(message)


class ValidationException(APIException):
    """Exception for validation errors."""

    def __init__(self, message, details=None, code=None):
        super().__init__(
            message, code or "validation_error", status.HTTP_400_BAD_REQUEST
        )
        self.details = details or {}


class NotFoundException(APIException):
    """Exception for resource not found."""

    def __init__(self, message, code=None):
        super().__init__(message, code or "not_found", status.HTTP_404_NOT_FOUND)


class UnauthorizedException(APIException):
    """Exception for authentication failures."""

    def __init__(self, message, code=None):
        super().__init__(message, code or "unauthorized", status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(APIException):
    """Exception for permission denied."""

    def __init__(self, message, code=None):
        super().__init__(message, code or "forbidden", status.HTTP_403_FORBIDDEN)


class ConflictException(APIException):
    """Exception for resource conflicts."""

    def __init__(self, message, code=None):
        super().__init__(message, code or "conflict", status.HTTP_409_CONFLICT)


class RateLimitException(APIException):
    """Exception for rate limiting."""

    def __init__(self, message, code=None):
        super().__init__(
            message, code or "rate_limit_exceeded", status.HTTP_429_TOO_MANY_REQUESTS
        )


class InternalServerException(APIException):
    """Exception for internal server errors."""

    def __init__(self, message, code=None):
        super().__init__(
            message, code or "internal_error", status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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

    if isinstance(exc, APIException):
        return Response(
            {
                "error": True,
                "message": exc.message,
                "code": exc.code,
                "details": getattr(exc, "details", {}),
            },
            status=exc.status_code,
        )

    detail = response.data
    error_code = "api_error"

    if isinstance(detail, dict):
        if "detail" in detail:
            message = str(detail["detail"])
            error_code = "validation_error"
        else:
            message = "Validation failed."
            detail = detail
    else:
        message = str(detail)
        detail = {}

    response.data = {
        "error": True,
        "message": message,
        "code": error_code,
        "details": detail if isinstance(detail, dict) else {},
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
