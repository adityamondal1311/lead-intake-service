"""Domain errors and the handlers that turn every failure into the same JSON error envelope:

    {"error": {"code", "message", "details", "requestId"}}

Unexpected exceptions are not handled here but in the request middleware, so their 500 response
still carries the request id (see app.core.middleware).
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_var
from app.schemas.common import ErrorBody, ErrorResponse


class AppError(Exception):
    """An expected failure the client can act on. Raised by services, which never import FastAPI."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "BAD_REQUEST"

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class LeadNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "LEAD_NOT_FOUND"

    def __init__(self) -> None:
        super().__init__("Lead not found")


class InvalidSignatureError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "INVALID_SIGNATURE"

    def __init__(self) -> None:
        # Deliberately unspecific: the caller learns nothing about why the signature failed.
        super().__init__("Missing or invalid webhook signature")


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(
            code=code, message=message, details=details, request_id=request_id_var.get()
        )
    )
    return JSONResponse(
        status_code=status_code, content=body.model_dump(mode="json"), headers=headers
    )


# Framework-level HTTP errors (unknown route, wrong method) mapped to stable codes.
_HTTP_ERROR_CODES = {
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
}


async def _app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return error_response(exc.status_code, exc.code, exc.message, exc.details)


async def _validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # One entry per invalid field, e.g. {"location": "query", "field": "limit", "message": ...}.
    # The rejected input value is left out: it may be PII and the client already has it.
    details = [
        {
            "location": str(error["loc"][0]),
            "field": ".".join(str(part) for part in error["loc"][1:]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "VALIDATION_ERROR",
        "Request validation failed",
        details,
    )


async def _http_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    return error_response(
        exc.status_code,
        _HTTP_ERROR_CODES.get(exc.status_code, "HTTP_ERROR"),
        str(exc.detail),
        headers=exc.headers,  # e.g. the Allow header on 405
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
