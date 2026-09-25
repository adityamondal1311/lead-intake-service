import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status

from app.core.errors import error_response
from app.core.logging import request_id_var

logger = logging.getLogger("app.request")

REQUEST_ID_HEADER = "X-Request-ID"
# Accept a caller's request id only if it is short and plain, so it cannot inject into log lines.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


async def request_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Assign a request id, echo it back, and write one access log line per request.

    Only method, path, status and duration are logged: never bodies or query strings, which
    can contain PII (search terms, webhook payloads).

    Unexpected exceptions are turned into the 500 error envelope here rather than by a FastAPI
    exception handler: Starlette runs the catch-all handler outside all middleware, where the
    request id is already gone, so the client would get no id to report.
    """
    incoming = request.headers.get(REQUEST_ID_HEADER, "")
    request_id = incoming if _VALID_REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    try:
        try:
            response = await call_next(request)
        except Exception:
            # Full traceback goes to the logs only; the client gets a generic message.
            logger.exception("unhandled error")
            response = error_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Internal server error"
            )
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            },
        )
        return response
    finally:
        request_id_var.reset(token)
