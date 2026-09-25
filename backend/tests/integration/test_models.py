"""Database-level guarantees of the data model.

These run against real PostgreSQL on purpose: the point is to prove the constraints live in the
database itself, so they hold even when two requests race or code bypasses the ORM.
"""

import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Activity, Lead, WebhookEvent
from app.models.enums import ActivityType, LeadStatus, WebhookOutcome


def _lead(external_id: str = "meta_lead_1", **fields: object) -> Lead:
    return Lead(external_id=external_id, full_name="Rahul Sharma", **fields)


def _webhook_event(external_event_id: str = "evt_1", source: str = "META_ADS") -> WebhookEvent:
    return WebhookEvent(source=source, external_event_id=external_event_id, payload={})


# --- defaults ---------------------------------------------------------------------------------


def test_new_lead_defaults_to_new_status_meta_source_and_timestamps(db_session: Session) -> None:
    lead = _lead()
    db_session.add(lead)
    db_session.commit()

    assert lead.status == LeadStatus.NEW
    assert lead.source == "META_ADS"
    assert lead.created_at is not None
    assert lead.created_at.tzinfo is not None  # timestamptz, not naive
    assert lead.updated_at == lead.created_at


def test_database_fills_defaults_for_rows_written_without_the_orm(db_session: Session) -> None:
    lead_id, activity_id = uuid.uuid4(), uuid.uuid4()
    db_session.execute(
        text("INSERT INTO leads (id, external_id, full_name) VALUES (:id, 'raw_1', 'Raw')"),
        {"id": lead_id},
    )
    db_session.execute(
        text(
            "INSERT INTO activities (id, lead_id, type, actor) "
            "VALUES (:id, :lead_id, 'LEAD_CREATED', 'test')"
        ),
        {"id": activity_id, "lead_id": lead_id},
    )
    db_session.commit()

    lead = db_session.get_one(Lead, lead_id)
    activity = db_session.get_one(Activity, activity_id)
    assert (lead.status, lead.source) == ("NEW", "META_ADS")
    assert activity.details == {}
    assert activity.created_at is not None


# --- uniqueness: lead identity and delivery idempotency ---------------------------------------


def test_duplicate_meta_lead_id_is_rejected(db_session: Session) -> None:
    db_session.add(_lead("meta_lead_1"))
    db_session.commit()

    db_session.add(_lead("meta_lead_1"))
    with pytest.raises(IntegrityError, match="uq_leads_external_id"):
        db_session.commit()


def test_same_event_id_from_same_source_is_rejected(db_session: Session) -> None:
    db_session.add(_webhook_event("evt_1"))
    db_session.commit()

    db_session.add(_webhook_event("evt_1"))
    with pytest.raises(IntegrityError, match="uq_webhook_events_source_external_event_id"):
        db_session.commit()


def test_same_event_id_from_a_different_source_is_allowed(db_session: Session) -> None:
    # Uniqueness is per (source, event id): another provider may reuse the same id format.
    db_session.add_all([_webhook_event("evt_1", "META_ADS"), _webhook_event("evt_1", "OTHER")])
    db_session.commit()

    assert len(db_session.scalars(select(WebhookEvent)).all()) == 2


# --- CHECK constraints -------------------------------------------------------------------------


@pytest.mark.parametrize("status", list(LeadStatus))
def test_every_lead_status_in_the_enum_passes_the_check(
    db_session: Session, status: LeadStatus
) -> None:
    db_session.add(_lead(status=status))
    db_session.commit()


def test_unknown_lead_status_is_rejected(db_session: Session) -> None:
    db_session.add(_lead(status="WON"))
    with pytest.raises(IntegrityError, match="ck_leads_status"):
        db_session.commit()


@pytest.mark.parametrize("activity_type", list(ActivityType))
def test_every_activity_type_in_the_enum_passes_the_check(
    db_session: Session, activity_type: ActivityType
) -> None:
    lead = _lead()
    db_session.add(lead)
    db_session.flush()
    db_session.add(Activity(lead_id=lead.id, type=activity_type, actor="test"))
    db_session.commit()


def test_unknown_activity_type_is_rejected(db_session: Session) -> None:
    lead = _lead()
    db_session.add(lead)
    db_session.flush()
    db_session.add(Activity(lead_id=lead.id, type="LEAD_DELETED", actor="test"))
    with pytest.raises(IntegrityError, match="ck_activities_type"):
        db_session.commit()


def test_webhook_outcome_may_be_null_while_processing_but_not_unknown(
    db_session: Session,
) -> None:
    pending = _webhook_event("evt_pending")
    db_session.add(pending)
    db_session.commit()
    assert pending.outcome is None

    db_session.add(
        WebhookEvent(source="META_ADS", external_event_id="evt_2", payload={}, outcome="IGNORED")
    )
    with pytest.raises(IntegrityError, match="ck_webhook_events_outcome"):
        db_session.commit()


def test_webhook_outcome_accepts_every_enum_value(db_session: Session) -> None:
    db_session.add_all(
        WebhookEvent(source="META_ADS", external_event_id=f"evt_{o}", payload={}, outcome=o)
        for o in WebhookOutcome
    )
    db_session.commit()


# --- foreign keys ------------------------------------------------------------------------------


def test_activity_for_a_missing_lead_is_rejected(db_session: Session) -> None:
    db_session.add(Activity(lead_id=uuid.uuid4(), type=ActivityType.LEAD_CREATED, actor="test"))
    with pytest.raises(IntegrityError, match="fk_activities_lead_id_leads"):
        db_session.commit()


def test_deleting_a_lead_removes_its_activities_but_keeps_webhook_events(
    db_session: Session,
) -> None:
    lead = _lead()
    db_session.add(lead)
    db_session.flush()
    db_session.add(Activity(lead_id=lead.id, type=ActivityType.LEAD_CREATED, actor="test"))
    event = WebhookEvent(source="META_ADS", external_event_id="evt_1", payload={}, lead_id=lead.id)
    db_session.add(event)
    db_session.commit()

    db_session.delete(lead)
    db_session.commit()

    assert db_session.scalars(select(Activity)).all() == []
    db_session.refresh(event)
    assert event.lead_id is None  # delivery record survives, detached from the deleted lead


# --- migrations --------------------------------------------------------------------------------


def test_models_and_migrations_are_in_sync(alembic_config: Config) -> None:
    # Fails if a model was changed without generating a migration.
    command.check(alembic_config)


def test_migrations_downgrade_to_empty_and_upgrade_again(
    alembic_config: Config, db_session: Session
) -> None:
    command.downgrade(alembic_config, "base")
    remaining = db_session.scalars(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
        )
    ).all()
    db_session.rollback()
    command.upgrade(alembic_config, "head")

    assert remaining == []
