"""Webhook idempotency, repeat events and concurrency, against real PostgreSQL.

The concurrent tests send real HTTP requests from several threads, released together by a
barrier, through one TestClient; the sync endpoints then run in parallel in the server's
threadpool, each with its own session and transaction. Each scenario is repeated because a race
can pass by luck in a single run.
"""

import threading
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Activity, Lead, WebhookEvent
from app.models.enums import ActivityType, LeadStatus, WebhookOutcome
from tests.integration.webhook_support import counts, payload, post_payload

pytestmark = pytest.mark.usefixtures("webhook_settings")

ROUNDS = range(3)


def _run_concurrently(calls: list[Callable[[], Response]]) -> list[Response]:
    start = threading.Barrier(len(calls))
    responses: list[Response | None] = [None] * len(calls)
    errors: list[BaseException] = []

    def run(index: int) -> None:
        try:
            start.wait()
            responses[index] = calls[index]()
        except BaseException as exc:  # surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(len(calls))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert errors == []
    return [r for r in responses if r is not None]


def _lead(session: Session, external_id: str) -> Lead:
    session.expire_all()
    return session.scalars(select(Lead).where(Lead.external_id == external_id)).one()


def _activities(session: Session, lead: Lead) -> list[Activity]:
    """The lead's activities, oldest first."""
    session.expire_all()
    return list(
        session.scalars(
            select(Activity)
            .where(Activity.lead_id == lead.id)
            .order_by(Activity.created_at, Activity.id)
        )
    )


def _event(session: Session, event_id: str) -> WebhookEvent:
    session.expire_all()
    return session.scalars(
        select(WebhookEvent).where(WebhookEvent.external_event_id == event_id)
    ).one()


# --- duplicate deliveries ----------------------------------------------------------------------


@pytest.mark.parametrize("round_", ROUNDS)
def test_same_event_delivered_five_times_at_once_is_processed_exactly_once(
    client: TestClient, db_session: Session, round_: int
) -> None:
    body = payload(event_id=f"evt_dup_{round_}", lead_id=f"meta_lead_dup_{round_}")

    responses = _run_concurrently([lambda: post_payload(client, body)] * 5)

    assert [r.status_code for r in responses] == [200] * 5  # no 500s
    statuses = sorted(r.json()["status"] for r in responses)
    assert statuses == ["duplicate"] * 4 + ["processed"]
    assert counts(db_session) == (1, 1, 1)


# --- repeat events for one lead ---------------------------------------------------------------


def test_changed_fields_record_lead_updated_diff_and_keep_the_sales_status(
    client: TestClient, db_session: Session
) -> None:
    post_payload(client, payload(event_id="evt_1", phone="+911111111111", campaign_id="cmp_a"))
    lead = _lead(db_session, "meta_lead_1")
    assert client.patch(f"/leads/{lead.id}/status", json={"status": "CONTACTED"}).status_code == 200

    response = post_payload(
        client, payload(event_id="evt_2", phone="+912222222222", campaign_id="cmp_b")
    )

    assert response.json()["outcome"] == "UPDATED"
    lead = _lead(db_session, "meta_lead_1")
    assert (lead.phone, lead.campaign_id) == ("+912222222222", "cmp_b")
    assert lead.status == LeadStatus.CONTACTED  # the webhook never changes the sales status
    update = _activities(db_session, lead)[-1]
    assert update.type == ActivityType.LEAD_UPDATED
    assert update.actor == "system:meta_webhook"
    assert update.details == {
        "changes": {
            "phone": {"from": "+911111111111", "to": "+912222222222"},
            "campaignId": {"from": "cmp_a", "to": "cmp_b"},
        },
        "externalEventId": "evt_2",
        "webhookEventId": str(_event(db_session, "evt_2").id),
    }
    assert _event(db_session, "evt_2").outcome == WebhookOutcome.UPDATED


def test_identical_event_is_unchanged_with_no_activity_but_is_recorded(
    client: TestClient, db_session: Session
) -> None:
    post_payload(client, payload(event_id="evt_1"))
    lead_before = _lead(db_session, "meta_lead_1")
    updated_at = lead_before.updated_at

    response = post_payload(client, payload(event_id="evt_2"))  # same data, new event

    assert response.json()["outcome"] == "UNCHANGED"
    lead = _lead(db_session, "meta_lead_1")
    assert [a.type for a in _activities(db_session, lead)] == [ActivityType.LEAD_CREATED]
    assert lead.updated_at == updated_at  # nothing was written to the lead
    event = _event(db_session, "evt_2")
    assert (event.outcome, event.lead_id) == (WebhookOutcome.UNCHANGED, lead.id)
    assert counts(db_session) == (1, 1, 2)


def test_missing_fields_do_not_erase_stored_data(client: TestClient, db_session: Session) -> None:
    post_payload(client, payload(event_id="evt_1", email="rahul@example.com", phone="+911"))

    later: dict[str, Any] = payload(event_id="evt_2", phone="+912", campaign_id="")
    del later["email"]  # absent; campaign_id blank
    post_payload(client, later)

    lead = _lead(db_session, "meta_lead_1")
    assert lead.email == "rahul@example.com"
    assert lead.campaign_id == "cmp_1"
    assert lead.phone == "+912"
    assert _activities(db_session, lead)[-1].details["changes"] == {
        "phone": {"from": "+911", "to": "+912"}
    }


def test_timeline_shows_creation_then_updates_in_order(
    client: TestClient, db_session: Session
) -> None:
    for n, phone in enumerate(["+911", "+912", "+913"], start=1):
        post_payload(client, payload(event_id=f"evt_{n}", phone=phone))
    lead = _lead(db_session, "meta_lead_1")

    timeline = client.get(f"/leads/{lead.id}").json()["activities"]  # newest first

    assert [a["type"] for a in timeline] == ["LEAD_UPDATED", "LEAD_UPDATED", "LEAD_CREATED"]
    assert [a["details"].get("changes", {}).get("phone", {}).get("to") for a in timeline] == [
        "+913",
        "+912",
        None,
    ]


# --- concurrency: different events for one lead ------------------------------------------------


@pytest.mark.parametrize("round_", ROUNDS)
def test_different_events_for_one_new_lead_at_once_create_it_once(
    client: TestClient, db_session: Session, round_: int
) -> None:
    """Delivery idempotency does not help here (the event ids differ); the lead's own unique key
    and the race-safe insert must ensure exactly one lead and one LEAD_CREATED."""
    lead_id = f"meta_lead_race_{round_}"
    bodies = [
        payload(event_id=f"evt_race_{round_}_{n}", lead_id=lead_id, phone=f"+9100{n}")
        for n in range(4)
    ]

    responses = _run_concurrently([lambda b=b: post_payload(client, b) for b in bodies])

    assert [r.status_code for r in responses] == [200] * 4  # no 500s
    outcomes = sorted(r.json()["outcome"] for r in responses)
    assert outcomes.count("CREATED") == 1
    assert set(outcomes) <= {"CREATED", "UPDATED"}  # each later event changes the phone

    lead = _lead(db_session, lead_id)
    activities = _activities(db_session, lead)
    assert [a.type for a in activities].count(ActivityType.LEAD_CREATED) == 1
    assert activities[0].type == ActivityType.LEAD_CREATED
    # The row lock serializes the updates, so each diff starts where the previous one ended
    # and the chain ends at the stored value.
    phone = next(
        b["phone"] for b in bodies if b["event_id"] == activities[0].details["externalEventId"]
    )
    for update in activities[1:]:
        assert update.details["changes"]["phone"]["from"] == phone
        phone = update.details["changes"]["phone"]["to"]
    assert lead.phone == phone
    assert counts(db_session) == (1, len(activities), 4)


@pytest.mark.parametrize("round_", ROUNDS)
def test_dashboard_status_change_and_webhook_update_at_once_both_survive(
    client: TestClient, db_session: Session, round_: int
) -> None:
    post_payload(client, payload(event_id=f"evt_{round_}_a", phone="+911"))
    lead = _lead(db_session, "meta_lead_1")

    responses = _run_concurrently(
        [
            lambda: client.patch(f"/leads/{lead.id}/status", json={"status": "CONTACTED"}),
            lambda: post_payload(client, payload(event_id=f"evt_{round_}_b", phone="+912")),
        ]
    )

    assert [r.status_code for r in responses] == [200, 200]
    lead = _lead(db_session, "meta_lead_1")
    assert (lead.status, lead.phone) == (LeadStatus.CONTACTED, "+912")
    assert sorted(a.type for a in _activities(db_session, lead)) == sorted(
        [ActivityType.LEAD_CREATED, ActivityType.STATUS_CHANGED, ActivityType.LEAD_UPDATED]
    )
