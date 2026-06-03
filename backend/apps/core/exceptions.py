from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return Response(
            {"error": True, "message": "An unexpected error occurred.", "details": {}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    detail = response.data
    if isinstance(detail, dict) and "detail" in detail:
        message = str(detail["detail"])
        details = {}
    elif isinstance(detail, dict):
        message = "Validation failed."
        details = detail
    else:
        message = str(detail)
        details = {}

    response.data = {"error": True, "message": message, "details": details}
    return response
