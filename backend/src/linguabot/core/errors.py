"""Единый формат ошибок API.

Контракт LinguaBot: ответ об ошибке содержит объект ``error`` с полями
``code`` (машинный код), ``message`` (понятное объяснение) и ``field``
(поле с ошибкой или ``null``).
"""

from dataclasses import dataclass

# Соответствие HTTP-статусов машинным кодам ошибок.
STATUS_CODE_MAP: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "too_many_requests",
    500: "internal_error",
    503: "service_unavailable",
}


@dataclass
class APIError(Exception):
    """Ошибка API, которая сериализуется в конверт ``{"error": {...}}``."""

    status_code: int
    code: str
    message: str
    field: str | None = None


def error_payload(code: str, message: str, field: str | None = None) -> dict:
    return {"error": {"code": code, "message": message, "field": field}}
