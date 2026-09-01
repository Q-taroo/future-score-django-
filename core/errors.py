"""Unified JSON API error shape (spec §32) — mirrors what the vote/resolve
endpoints return so the frontend never has to guess the response format.
Internal error details are logged server-side, never leaked to the client.
"""

import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, message: str, status: int = 400, code: str = "APP_ERROR"):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


def error_response(message: str, status: int = 400, code: str = "APP_ERROR") -> JsonResponse:
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def handle_exception(exc: Exception) -> JsonResponse:
    if isinstance(exc, AppError):
        return error_response(exc.message, exc.status, exc.code)
    logger.exception("unhandled error in API view")
    return error_response("サーバーエラーが発生しました。しばらくしてから再度お試しください。", 500, "INTERNAL_ERROR")
