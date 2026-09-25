import threading
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Activity, Lead
from app.models.enums import ActivityType, LeadStatus
from app.services import lead_service

BASE_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def _add_lead(
    session: Session, n: int, *, minutes_ago: int | None = None, **fields: object
) -> Lead:
    """Insert a lead; by default lead n is n minutes older than BASE_TIME (so 0 is newest)."""
    created = BASE_TIME - timedelta(minutes=n if minutes_ago is None else minutes_ago)
    values: dict[str, object] = {
        "external_id": f"meta_lead_{n}",
        "full_name": f"Lead {n}",
        "email": f"lead{n}@example.com",
        "phone": f"+91900000{n:04d}",
        "created_at": created,
        "updated_at": created,
    }
    values.update(fields)
    lead = Lead(**values)
    session.add(lead)
    session.commit()
    return lead


def _names(response_json: dict) -> list[str]:
    return [lead["fullName"] for lead in response_json["data"]]


# --- GET /leads -------------------------------------------------------------------------------


def test_list_is_empty_with_zero_pages_when_there_are_no_leads(client: TestClient) -> None:
    response = client.get("/leads")

    assert response.status_code == 200
    assert response.json() == {
        "data": [],
        "pagination": {"page": 1, "limit": 20, "total": 0, "totalPages": 0},
    }


def test_list_returns_newest_first_and_paginates(client: TestClient, db_session: Session) -> None:
    for n in range(5):
        _add_lead(db_session, n)

    first = client.get("/leads", params={"limit": 2}).json()
    last = client.get("/leads", params={"limit": 2, "page": 3}).json()

    assert _names(first) == ["Lead 0", "Lead 1"]
    assert first["pagination"] == {"page": 1, "limit": 2, "total": 5, "totalPages": 3}
    assert _names(last) == ["Lead 4"]


def test_page_past_the_end_returns_empty_data_with_correct_totals(
    client: TestClient, db_session: Session
) -> None:
    _add_lead(db_session, 0)

    body = client.get("/leads", params={"page": 5}).json()

    assert body["data"] == []
    assert body["pagination"]["total"] == 1
    assert body["pagination"]["totalPages"] == 1


def test_pages_neither_skip_nor_repeat_leads_with_identical_timestamps(
    client: TestClient, db_session: Session
) -> None:
    for n in range(6):
        _add_lead(db_session, n, minutes_ago=0)  # all created at the same instant

    seen = [
        lead["id"]
        for page in (1, 2, 3)
        for lead in client.get("/leads", params={"limit": 2, "page": page}).json()["data"]
    ]

    assert len(seen) == 6
    assert len(set(seen)) == 6


def test_status_filter_returns_only_matching_leads(client: TestClient, db_session: Session) -> None:
    _add_lead(db_session, 0, status=LeadStatus.NEW)
    _add_lead(db_session, 1, status=LeadStatus.LOST)
    _add_lead(db_session, 2, status=LeadStatus.LOST)

    body = client.get("/leads", params={"status": "LOST"}).json()

    assert _names(body) == ["Lead 1", "Lead 2"]
    assert body["pagination"]["total"] == 2


@pytest.mark.parametrize("term", ["rAhUl", "RAHUL@EXAMPLE", "98765"])
def test_search_matches_name_email_or_phone_case_insensitively(
    client: TestClient, db_session: Session, term: str
) -> None:
    _add_lead(db_session, 0, full_name="Rahul Sharma", email="rahul@example.com", phone="+9198765")
    _add_lead(db_session, 1, full_name="Priya Patel", email="priya@example.com", phone="+9111111")

    assert _names(client.get("/leads", params={"search": term}).json()) == ["Rahul Sharma"]


def test_search_treats_like_wildcards_literally(client: TestClient, db_session: Session) -> None:
    _add_lead(db_session, 0, full_name="50% Discount Seeker")
    _add_lead(db_session, 1, full_name="Plain Name", email="plain_name@example.com")
    _add_lead(db_session, 2, full_name="Other", email="other@example.com")

    assert _names(client.get("/leads", params={"search": "%"}).json()) == ["50% Discount Seeker"]
    assert _names(client.get("/leads", params={"search": "_"}).json()) == ["Plain Name"]


def test_blank_search_is_ignored(client: TestClient, db_session: Session) -> None:
    _add_lead(db_session, 0)
    _add_lead(db_session, 1)

    body = client.get("/leads", params={"search": "   "}).json()

    assert body["pagination"]["total"] == 2


def test_status_filter_and_search_combine(client: TestClient, db_session: Session) -> None:
    _add_lead(db_session, 0, full_name="Rahul A", status=LeadStatus.NEW)
    _add_lead(db_session, 1, full_name="Rahul B", status=LeadStatus.LOST)

    body = client.get("/leads", params={"search": "rahul", "status": "LOST"}).json()

    assert _names(body) == ["Rahul B"]


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"page": 0}, "page"),
        ({"limit": 0}, "limit"),
        ({"limit": 101}, "limit"),
        ({"status": "WON"}, "status"),
        ({"search": "x" * 101}, "search"),
        ({"page": "abc"}, "page"),
    ],
)
def test_invalid_list_parameters_return_the_validation_envelope(
    client: TestClient, params: dict[str, object], field: str
) -> None:
    response = client.get("/leads", params=params)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["requestId"] == response.headers["X-Request-ID"]
    assert [(d["location"], d["field"]) for d in error["details"]] == [("query", field)]


def test_list_items_use_camel_case_summary_fields(client: TestClient, db_session: Session) -> None:
    _add_lead(db_session, 0, campaign_id="cmp_1")

    item = client.get("/leads").json()["data"][0]

    assert set(item) == {
        "id",
        "fullName",
        "email",
        "phone",
        "status",
        "source",
        "campaignId",
        "createdAt",
    }


# --- GET /leads/{id} --------------------------------------------------------------------------


def test_detail_returns_lead_and_activities_newest_first(
    client: TestClient, db_session: Session
) -> None:
    lead = _add_lead(db_session, 0, form_id="form_1", ad_id="ad_1")
    db_session.add_all(
        [
            Activity(
                lead_id=lead.id,
                type=ActivityType.LEAD_CREATED,
                actor="system:meta_webhook",
                created_at=BASE_TIME,
            ),
            Activity(
                lead_id=lead.id,
                type=ActivityType.STATUS_CHANGED,
                actor="user:dashboard",
                details={"from": "NEW", "to": "CONTACTED"},
                created_at=BASE_TIME + timedelta(minutes=5),
            ),
        ]
    )
    db_session.commit()

    response = client.get(f"/leads/{lead.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["lead"]["id"] == str(lead.id)
    assert body["lead"]["externalId"] == "meta_lead_0"
    assert (body["lead"]["formId"], body["lead"]["adId"]) == ("form_1", "ad_1")
    assert [a["type"] for a in body["activities"]] == ["STATUS_CHANGED", "LEAD_CREATED"]
    assert body["activities"][0]["details"] == {"from": "NEW", "to": "CONTACTED"}


def test_detail_of_unknown_lead_returns_404_envelope(client: TestClient) -> None:
    response = client.get(f"/leads/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "LEAD_NOT_FOUND"


def test_detail_with_malformed_id_returns_422_envelope(client: TestClient) -> None:
    response = client.get("/leads/not-a-uuid")

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "lead_id"


# --- PATCH /leads/{id}/status -----------------------------------------------------------------


def _activities(session: Session, lead_id: uuid.UUID) -> list[Activity]:
    session.expire_all()
    return list(session.scalars(select(Activity).where(Activity.lead_id == lead_id)))


def test_status_change_updates_lead_and_records_activity(
    client: TestClient, db_session: Session
) -> None:
    lead = _add_lead(db_session, 0)

    response = client.patch(f"/leads/{lead.id}/status", json={"status": "CONTACTED"})

    assert response.status_code == 200
    body = response.json()
    assert body["lead"]["status"] == "CONTACTED"
    assert body["activity"]["type"] == "STATUS_CHANGED"
    assert body["activity"]["actor"] == "user:dashboard"
    assert body["activity"]["details"] == {"from": "NEW", "to": "CONTACTED"}

    # Persisted, and visible on the timeline straight away.
    timeline = client.get(f"/leads/{lead.id}").json()["activities"]
    assert [a["id"] for a in timeline] == [body["activity"]["id"]]
    db_session.refresh(lead)
    assert lead.status == LeadStatus.CONTACTED
    assert lead.updated_at > BASE_TIME


def test_setting_the_same_status_is_a_no_op(client: TestClient, db_session: Session) -> None:
    lead = _add_lead(db_session, 0, status=LeadStatus.QUALIFIED)

    response = client.patch(f"/leads/{lead.id}/status", json={"status": "QUALIFIED"})

    assert response.status_code == 200
    assert response.json()["activity"] is None
    assert _activities(db_session, lead.id) == []
    db_session.refresh(lead)
    assert lead.updated_at == BASE_TIME  # nothing was written


def test_invalid_status_is_rejected_and_nothing_changes(
    client: TestClient, db_session: Session
) -> None:
    lead = _add_lead(db_session, 0)

    response = client.patch(f"/leads/{lead.id}/status", json={"status": "WON"})

    assert response.status_code == 422
    assert response.json()["error"]["details"][0] == {
        "location": "body",
        "field": "status",
        "message": "Input should be 'NEW', 'CONTACTED', 'QUALIFIED', 'CONVERTED' or 'LOST'",
    }
    db_session.refresh(lead)
    assert lead.status == LeadStatus.NEW
    assert _activities(db_session, lead.id) == []


def test_status_change_for_unknown_lead_returns_404(client: TestClient) -> None:
    response = client.patch(f"/leads/{uuid.uuid4()}/status", json={"status": "LOST"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "LEAD_NOT_FOUND"


def test_status_change_is_rolled_back_when_the_activity_insert_fails(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    lead = _add_lead(db_session, 0)
    # A real database failure on the activity INSERT: actor is VARCHAR(64), so Postgres rejects
    # this value. The status UPDATE has already been sent in the same transaction by then.
    monkeypatch.setattr(lead_service, "DASHBOARD_ACTOR", "x" * 65)

    response = client.patch(f"/leads/{lead.id}/status", json={"status": "CONTACTED"})

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "INTERNAL_ERROR"
    assert error["message"] == "Internal server error"  # no internals leaked
    assert error["requestId"] == response.headers["X-Request-ID"]
    # Atomicity: the status change did not survive without its audit entry.
    db_session.refresh(lead)
    assert lead.status == LeadStatus.NEW
    assert _activities(db_session, lead.id) == []


def _change_concurrently(lead_id: uuid.UUID, targets: list[LeadStatus]) -> None:
    """Run one status change per target in its own thread and session, all released at once."""
    start = threading.Barrier(len(targets))
    errors: list[BaseException] = []

    def change(target: LeadStatus) -> None:
        try:
            with SessionLocal() as session:
                start.wait()
                lead_service.update_status(session, lead_id, target)
        except BaseException as exc:  # surfaced in the calling thread below
            errors.append(exc)

    threads = [threading.Thread(target=change, args=(t,)) for t in targets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert errors == []


@pytest.mark.parametrize("round_", range(5))  # repeated: a race can pass by luck once
def test_concurrent_status_changes_produce_a_consistent_ordered_audit_chain(
    client: TestClient, db_session: Session, round_: int
) -> None:
    """Four transactions change the same lead at the same moment.

    The row lock serializes them, so each STATUS_CHANGED 'from' is the status the previous one
    set: the activities form one unbroken chain NEW -> ... -> final status. Without the lock,
    several transactions read NEW and record from=NEW, breaking the chain.

    The timeline returned by the API must also list the changes in that real order. This failed
    when activities.created_at used now() (transaction start time) instead of clock_timestamp().
    """
    lead = _add_lead(db_session, round_)
    targets = [LeadStatus.CONTACTED, LeadStatus.QUALIFIED, LeadStatus.CONVERTED, LeadStatus.LOST]

    _change_concurrently(lead.id, targets)

    transitions = {a.details["from"]: a.details["to"] for a in _activities(db_session, lead.id)}
    assert len(transitions) == len(targets)  # no two activities share a "from"
    status, chain = "NEW", ["NEW"]
    while status in transitions:
        status = transitions[status]
        chain.append(status)
    db_session.refresh(lead)
    assert len(chain) == len(targets) + 1
    assert chain[-1] == lead.status

    timeline = client.get(f"/leads/{lead.id}").json()["activities"]  # newest first
    assert [a["details"]["to"] for a in reversed(timeline)] == chain[1:]
