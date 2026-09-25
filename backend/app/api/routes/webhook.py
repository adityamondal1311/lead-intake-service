from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app.api.deps import SettingsDep
from app.core.errors import ForbiddenError
from app.core.security import is_valid_verify_token
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/webhook", tags=["webhook"])


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
