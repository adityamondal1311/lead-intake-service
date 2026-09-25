import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

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
    """
    incoming = request.headers.get(REQUEST_ID_HEADER, "")
    request_id = incoming if _VALID_REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
    finally:
        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            },
        )
        request_id_var.reset(token)
