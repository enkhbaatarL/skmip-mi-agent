from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ValidationAppError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("VALIDATION_ERROR", message, 422, details)


class NotFoundAppError(AppError):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__("NOT_FOUND", f"{resource}을(를) 찾을 수 없습니다.", 404, {"id": resource_id})


class ConflictAppError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("CONFLICT", message, 409, details)


class ServiceUnavailableAppError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("SERVICE_UNAVAILABLE", message, 503, details)
