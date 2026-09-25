import json
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import compute_signature
from app.main import app
from app.models import Activity, Lead, WebhookEvent
from app.models.enums import ActivityType, LeadStatus, WebhookOutcome
from app.services import webhook_service

SECRET = "test-app-secret"
VERIFY_TOKEN = "test-verify-token"
URL = "/webhook/meta-lead"


@pytest.fixture(autouse=True)
def webhook_settings() -> Iterator[None]:
    # Explicit values, so a developer's backend/.env can never change what these tests see.
    app.dependency_overrides[get_settings] = lambda: Settings(
        meta_app_secret=SECRET, meta_verify_token=VERIFY_TOKEN
    )
    yield
    app.dependency_overrides.pop(get_settings, None)


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
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
    payload.update(overrides)
    return payload


def _post(
    client: TestClient, body: bytes, signature: str | None = "sign", secret: str = SECRET
) -> Response:
    headers = {"Content-Type": "application/json"}
    if signature == "sign":
        headers["X-Hub-Signature-256"] = compute_signature(secret, body)
    elif signature is not None:
        headers["X-Hub-Signature-256"] = signature
    return client.post(URL, content=body, headers=headers)


def _post_payload(client: TestClient, payload: dict[str, Any]) -> Response:
    return _post(client, json.dumps(payload).encode())


def _counts(session: Session) -> tuple[int, int, int]:
    session.expire_all()
    return tuple(  # type: ignore[return-value]
        session.scalar(select(func.count()).select_from(model)) or 0
        for model in (Lead, Activity, WebhookEvent)
    )


# --- successful ingestion --------------------------------------------------------------------


def test_signed_delivery_creates_lead_activity_and_delivery_record(
    client: TestClient, db_session: Session
) -> None:
    response = _post_payload(client, _payload())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processed"
    assert body["outcome"] == "CREATED"

    lead = db_session.scalars(select(Lead)).one()
    assert str(lead.id) == body["leadId"]
    assert lead.external_id == "meta_lead_1"
    assert lead.full_name == "Rahul Sharma"  # trimmed
    assert lead.email == "rahul.sharma@example.com"  # lowercased
    assert lead.status == LeadStatus.NEW
    assert (lead.campaign_id, lead.form_id, lead.ad_id) == ("cmp_1", "form_1", "ad_1")
    assert lead.meta_created_at is not None

    event = db_session.scalars(select(WebhookEvent)).one()
    assert event.external_event_id == "evt_1"
    assert event.lead_id == lead.id
    assert event.outcome == WebhookOutcome.CREATED
    assert event.processed_at is not None and event.processed_at >= event.received_at
    assert event.payload == _payload()  # raw payload stored verbatim, not the normalized one

    activity = db_session.scalars(select(Activity)).one()
    assert activity.lead_id == lead.id
    assert activity.type == ActivityType.LEAD_CREATED
    assert activity.actor == "system:meta_webhook"
    assert activity.details == {
        "source": "META_ADS",
        "webhookEventId": str(event.id),
        "externalEventId": "evt_1",
    }


def test_ingested_lead_is_served_by_the_lead_api_without_the_raw_payload(
    client: TestClient,
) -> None:
    lead_id = _post_payload(client, _payload()).json()["leadId"]

    listed = client.get("/leads").json()["data"]
    detail = client.get(f"/leads/{lead_id}").json()

    assert [lead["id"] for lead in listed] == [lead_id]
    assert [a["type"] for a in detail["activities"]] == ["LEAD_CREATED"]
    assert "payload" not in json.dumps(detail)
    assert "  Rahul Sharma " not in json.dumps(detail)  # only the normalized value is exposed


def test_redelivery_never_creates_a_second_lead_or_activity(
    client: TestClient, db_session: Session
) -> None:
    _post_payload(client, _payload())
    _post_payload(client, _payload())  # same event_id again

    # Guaranteed by the database constraints even before explicit idempotency handling.
    assert _counts(db_session) == (1, 1, 1)


# --- signature ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "signature",
    [
        pytest.param(None, id="missing"),
        pytest.param("sha256=" + "0" * 64, id="wrong"),
        pytest.param(compute_signature("another-secret", b"{}"), id="other-secret"),
    ],
)
def test_bad_signature_returns_401_and_stores_nothing(
    client: TestClient, db_session: Session, signature: str | None
) -> None:
    response = _post(client, json.dumps(_payload()).encode(), signature=signature)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_SIGNATURE"
    assert _counts(db_session) == (0, 0, 0)


def test_signature_over_a_different_body_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    signed = json.dumps(_payload()).encode()
    tampered = json.dumps(_payload(email="attacker@example.com")).encode()

    response = _post(client, tampered, signature=compute_signature(SECRET, signed))

    assert response.status_code == 401
    assert _counts(db_session) == (0, 0, 0)


def test_signature_is_checked_before_the_body_is_parsed(client: TestClient) -> None:
    # Unsigned garbage gets 401, not 422: unauthenticated callers learn nothing about validation.
    response = _post(client, b"not json", signature=None)

    assert response.status_code == 401


def test_unconfigured_secret_rejects_even_an_empty_key_signature(client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(meta_app_secret="")
    body = json.dumps(_payload()).encode()

    response = _post(client, body, signature=compute_signature("", body))

    assert response.status_code == 401


def test_oversized_body_is_rejected_before_signature_work(client: TestClient) -> None:
    response = _post(client, b"x" * (64 * 1024 + 1))

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


# --- payload validation ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "field"),
    [
        pytest.param(_payload(email=None, phone=None), "", id="no-contact"),
        pytest.param(_payload(email="not-an-email"), "email", id="bad-email"),
        pytest.param(_payload(lead_id=""), "lead_id", id="empty-lead-id"),
        pytest.param(_payload(created_time="2026-09-24T10:00:00"), "created_time", id="naive-time"),
    ],
)
def test_invalid_payload_returns_422_envelope_and_stores_nothing(
    client: TestClient, db_session: Session, body: dict[str, Any], field: str
) -> None:
    response = _post_payload(client, body)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [(d["location"], d["field"]) for d in error["details"]] == [("body", field)]
    assert _counts(db_session) == (0, 0, 0)


@pytest.mark.parametrize("raw", [b"not json", b"[1, 2]"])
def test_non_object_json_body_returns_422(client: TestClient, raw: bytes) -> None:
    response = _post(client, raw)

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["location"] == "body"


# --- atomicity ---------------------------------------------------------------------------------


def test_failure_after_lead_insert_rolls_back_the_whole_delivery(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A real database failure on the activity INSERT (actor is VARCHAR(64)), after the delivery
    # row and the lead have already been sent in the same transaction.
    monkeypatch.setattr(webhook_service, "WEBHOOK_ACTOR", "x" * 65)

    response = _post_payload(client, _payload())

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    # Nothing partially saved, including the delivery record, so Meta's retry starts clean.
    assert _counts(db_session) == (0, 0, 0)

    monkeypatch.undo()
    retry = _post_payload(client, _payload())
    assert retry.status_code == 200
    assert _counts(db_session) == (1, 1, 1)


# --- subscription handshake --------------------------------------------------------------------


def test_handshake_echoes_challenge_as_plain_text(client: TestClient) -> None:
    response = client.get(
        URL,
        params={"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "42"},
    )

    assert response.status_code == 200
    assert response.text == "42"
    assert response.headers["content-type"].startswith("text/plain")


@pytest.mark.parametrize(
    "params",
    [
        {"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "42"},
        {"hub.mode": "unsubscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "42"},
        {"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN},
        {},
    ],
)
def test_handshake_fails_with_403(client: TestClient, params: dict[str, str]) -> None:
    response = client.get(URL, params=params)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
