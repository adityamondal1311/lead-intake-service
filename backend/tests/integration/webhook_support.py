"""Helpers shared by the webhook integration tests: signed requests and row counts."""

import json
from typing import Any

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import compute_signature
from app.models import Activity, Lead, WebhookEvent

SECRET = "test-app-secret"
VERIFY_TOKEN = "test-verify-token"
URL = "/webhook/meta-lead"


def payload(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "event_id": "evt_1",
        "lead_id": "meta_lead_1",
        "created_time": "2026-09-24T10:00:00+0000",
        "campaign_id": "cmp_1",
        "form_id": "form_1",
        "ad_id": "ad_1",
        "full_name": "  Rahul Sharma ",
        "email": "Rahul.Sharma@Example.com",
        "phone": "+919999999999",
    }
    values.update(overrides)
    return values


def post(
    client: TestClient, body: bytes, signature: str | None = "sign", secret: str = SECRET
) -> Response:
    """POST a raw body; by default correctly signed, or with the given (or no) signature."""
    headers = {"Content-Type": "application/json"}
    if signature == "sign":
        headers["X-Hub-Signature-256"] = compute_signature(secret, body)
    elif signature is not None:
        headers["X-Hub-Signature-256"] = signature
    return client.post(URL, content=body, headers=headers)


def post_payload(client: TestClient, values: dict[str, Any]) -> Response:
    return post(client, json.dumps(values).encode())


def counts(session: Session) -> tuple[int, int, int]:
    """(leads, activities, webhook_events) currently stored."""
    session.expire_all()
    return (
        session.scalar(select(func.count()).select_from(Lead)) or 0,
        session.scalar(select(func.count()).select_from(Activity)) or 0,
        session.scalar(select(func.count()).select_from(WebhookEvent)) or 0,
    )
