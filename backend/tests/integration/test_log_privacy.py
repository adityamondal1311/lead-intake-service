"""No lead PII in server logs, on success and on every failure path.

Requests carry deliberately distinctive name/email/phone values; every log line the server emits
is captured through the production JSON formatter (so extras and tracebacks are included) and
searched for those exact values. Checking real values, rather than words like "email", proves
"the request contained PII, the logs did not".
"""

import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.logging import JsonFormatter
from app.repositories import lead_repository
from tests.integration.webhook_support import payload, post, post_payload

pytestmark = pytest.mark.usefixtures("webhook_settings")

NAME = "Zyxwvut Piitestperson"
EMAIL = "pii-test.zyxwvut@example.com"
PHONE = "+919876501234"
SENSITIVE = [NAME, "Piitestperson", EMAIL, "pii-test.zyxwvut", PHONE, "9876501234"]

# The test's own HTTP client (httpx) logs each request URL, including the query string. That
# log comes from the client side of the test, not the server, so it is excluded.
CLIENT_SIDE_LOGGERS = ("httpx", "httpcore")


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.setFormatter(JsonFormatter())
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if not record.name.startswith(CLIENT_SIDE_LOGGERS):
            self.lines.append(self.format(record))


@pytest.fixture
def server_logs() -> Iterator[list[str]]:
    capture = _Capture()
    root = logging.getLogger()
    previous_level = root.level
    root.addHandler(capture)
    root.setLevel(logging.DEBUG)  # stricter than production: nothing at any level may leak
    yield capture.lines
    root.removeHandler(capture)
    root.setLevel(previous_level)


def _pii_payload(event_id: str, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "event_id": event_id,
        "lead_id": f"meta_{event_id}",
        "full_name": NAME,
        "email": EMAIL,
        "phone": PHONE,
    }
    values.update(overrides)
    return payload(**values)


def _leaks(lines: list[str]) -> list[str]:
    return [value for value in SENSITIVE if any(value.lower() in line.lower() for line in lines)]


def test_no_pii_in_logs_across_success_and_failure_paths(
    client: TestClient, server_logs: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # 1. Successful ingestion.
    assert post_payload(client, _pii_payload("evt_ok")).status_code == 200
    # 2. Duplicate delivery.
    assert post_payload(client, _pii_payload("evt_ok")).json()["status"] == "duplicate"
    # 3. Repeat event that updates the lead (diff contains the old and new phone).
    update = _pii_payload("evt_update", lead_id="meta_evt_ok", phone=PHONE + "9")
    assert post_payload(client, update).json()["outcome"] == "UPDATED"
    # 4. Validation error (invalid email alongside the name and phone).
    bad = _pii_payload("evt_bad", email="not-an-email " + EMAIL)
    assert post_payload(client, bad).status_code == 422
    # 5. Rejected signature with a PII body.
    assert (
        post(client, json.dumps(_pii_payload("evt_sig")).encode(), signature=None).status_code
        == 401
    )
    # 6. Search for the lead by its email and phone (query strings are never logged).
    assert client.get("/leads", params={"search": EMAIL}).status_code == 200
    assert client.get("/leads", params={"search": PHONE}).status_code == 200
    # 7. Unexpected failure: a database error on the *lead* INSERT (an over-long ad_id), logged
    #    with its full traceback. That statement's parameters include the name, email and phone,
    #    so this is the path where SQLAlchemy would print PII unless parameters are hidden.
    #    (Failing the activity INSERT instead would not test this: its parameters hold no PII.)
    original_insert = lead_repository.insert_if_new

    def insert_with_overlong_ad_id(session: Session, *, external_id: str, **fields: Any) -> Any:
        return original_insert(session, external_id=external_id, **{**fields, "ad_id": "x" * 300})

    monkeypatch.setattr(lead_repository, "insert_if_new", insert_with_overlong_ad_id)
    assert post_payload(client, _pii_payload("evt_crash")).status_code == 500

    # The paths really ran and were logged (guards against an empty capture passing vacuously).
    text = "\n".join(server_logs)
    assert '"message": "webhook processed"' in text
    assert '"message": "webhook duplicate ignored"' in text
    assert '"message": "webhook signature rejected"' in text
    assert '"message": "unhandled error"' in text and '"exc_info": "Traceback' in text
    assert text.count('"message": "request completed"') >= 8

    assert _leaks(server_logs) == []
