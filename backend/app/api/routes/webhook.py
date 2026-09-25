import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
from pydantic import ValidationError

from app.api.deps import DbSession, SettingsDep
from app.core.errors import ForbiddenError, InvalidSignatureError, PayloadTooLargeError
from app.core.security import SIGNATURE_HEADER, is_valid_signature, is_valid_verify_token
from app.schemas.common import ErrorResponse
from app.schemas.webhook import MetaLeadPayload, WebhookAck
from app.services import webhook_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])

# A lead payload is a few hundred bytes; the cap stops an unauthenticated caller from making the
# server buffer an arbitrarily large body before the signature can be checked.
MAX_BODY_BYTES = 64 * 1024


@router.get(
    "/meta-lead",
    summary="Meta webhook subscription handshake",
    description="Called by Meta when the webhook is subscribed. If `hub.mode` is `subscribe` and "
    "`hub.verify_token` matches `META_VERIFY_TOKEN`, echoes `hub.challenge` as plain text; "
    "otherwise 403.",
    response_class=PlainTextResponse,
    responses={
        200: {"content": {"text/plain": {}}, "description": "The echoed challenge"},
        403: {"model": ErrorResponse, "description": "Verification failed"},
    },
)
def verify_subscription(
    settings: SettingsDep,
    mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    verify_token: Annotated[str | None, Query(alias="hub.verify_token", max_length=256)] = None,
    challenge: Annotated[str | None, Query(alias="hub.challenge", max_length=256)] = None,
) -> PlainTextResponse:
    if (
        mode != "subscribe"
        or not challenge
        or not is_valid_verify_token(settings.meta_verify_token, verify_token)
    ):
        raise ForbiddenError("Webhook verification failed")
    # Plain text, exactly as received: Meta compares the response body to the challenge it sent.
    return PlainTextResponse(challenge)


async def verified_webhook_body(request: Request, settings: SettingsDep) -> bytes:
    """Read the raw body and verify its signature before anything parses it.

    The HMAC covers the exact bytes Meta sent, so it must be checked on the raw body; re-encoding
    parsed JSON would not reproduce them. Checking first also means an unauthenticated caller
    gets a 401 and nothing else: no parsing work and no validation messages.

    Async so it can read the body; the route itself stays sync and runs in the threadpool.
    """
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BODY_BYTES:
            raise PayloadTooLargeError(MAX_BODY_BYTES)
    if not is_valid_signature(
        settings.meta_app_secret, bytes(body), request.headers.get(SIGNATURE_HEADER)
    ):
        logger.warning("webhook signature rejected")  # the header and body are never logged
        raise InvalidSignatureError()
    return bytes(body)


def _parse_payload(body: bytes) -> tuple[MetaLeadPayload, dict[str, Any]]:
    """Returns the validated payload and the raw JSON object (stored for audit/replay)."""
    try:
        raw = json.loads(body)
    except ValueError:
        raise RequestValidationError(
            [{"loc": ("body",), "msg": "Body must be valid JSON", "type": "json_invalid"}]
        ) from None
    if not isinstance(raw, dict):
        raise RequestValidationError(
            [{"loc": ("body",), "msg": "Body must be a JSON object", "type": "model_type"}]
        )
    try:
        payload = MetaLeadPayload.model_validate(raw)
    except ValidationError as exc:
        # Same 422 envelope as every other endpoint; locations prefixed with "body".
        raise RequestValidationError(
            [{**error, "loc": ("body", *error["loc"])} for error in exc.errors()]
        ) from None
    return payload, raw


@router.post(
    "/meta-lead",
    summary="Receive a Meta lead",
    # A duplicate is acknowledged with just {"status": "duplicate"} (no null fields).
    response_model_exclude_none=True,
    description="Requires a valid `X-Hub-Signature-256` (HMAC-SHA256 of the raw body keyed with "
    "`META_APP_SECRET`). Stores the delivery, creates the lead and records a `LEAD_CREATED` "
    "activity in one transaction. The body is the normalized post-enrichment payload "
    "(see `MetaLeadPayload`).",
    responses={
        200: {
            "description": "Processed, or acknowledged as a duplicate delivery",
            "content": {
                "application/json": {
                    "examples": {
                        "created": {
                            "summary": "New lead",
                            "value": {
                                "status": "processed",
                                "outcome": "CREATED",
                                "leadId": "0b6f1c9e-3a4d-4c2b-9e8f-7a6b5c4d3e2f",
                            },
                        },
                        "updated": {
                            "summary": "Existing lead, fields changed",
                            "value": {
                                "status": "processed",
                                "outcome": "UPDATED",
                                "leadId": "0b6f1c9e-3a4d-4c2b-9e8f-7a6b5c4d3e2f",
                            },
                        },
                        "duplicate": {
                            "summary": "Same event delivered again",
                            "value": {"status": "duplicate"},
                        },
                    }
                }
            },
        },
        401: {"model": ErrorResponse, "description": "Missing or invalid signature"},
        413: {"model": ErrorResponse, "description": "Body too large"},
        422: {"model": ErrorResponse, "description": "Invalid payload"},
    },
    # The route reads raw bytes (needed for the signature), so FastAPI cannot infer the body
    # schema; document it explicitly so /docs still shows the payload.
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": MetaLeadPayload.model_json_schema()}},
        }
    },
)
def receive_meta_lead(
    db: DbSession, body: Annotated[bytes, Depends(verified_webhook_body)]
) -> WebhookAck:
    payload, raw = _parse_payload(body)
    result = webhook_service.process_meta_lead(db, payload, raw)
    if result.is_duplicate:
        # 2xx so Meta stops retrying: from the sender's side the delivery did succeed earlier.
        return WebhookAck(status="duplicate")
    return WebhookAck(status="processed", outcome=result.outcome, lead_id=result.lead_id)
