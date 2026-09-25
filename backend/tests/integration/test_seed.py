import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Activity, Lead
from app.models.enums import ActivityType
from scripts import seed
from tests.integration.webhook_support import counts


def _activity_types(session: Session) -> dict[str, int]:
    session.expire_all()
    rows = session.execute(select(Activity.type, func.count()).group_by(Activity.type)).all()
    return {activity_type: count for activity_type, count in rows}


def test_seed_goes_through_the_real_services_and_builds_an_audit_trail(
    db_session: Session,
) -> None:
    tally = seed.seed()

    leads, _, deliveries = counts(db_session)
    assert leads == len(seed.PEOPLE)
    assert deliveries == len(seed.PEOPLE) + len(seed.FOLLOW_UPS)
    assert tally["CREATED"] == len(seed.PEOPLE)
    assert tally["UNCHANGED"] == 1  # the identical follow-up
    assert tally["UPDATED"] == len(seed.FOLLOW_UPS) - 1
    types = _activity_types(db_session)
    assert types[ActivityType.LEAD_CREATED] == len(seed.PEOPLE)
    assert types[ActivityType.LEAD_UPDATED] == tally["UPDATED"]
    assert types[ActivityType.STATUS_CHANGED] == tally["status_changes"] > 0
    # Every status appears, including a reopened lead.
    statuses = set(db_session.scalars(select(Lead.status)))
    assert statuses == {"NEW", "CONTACTED", "QUALIFIED", "CONVERTED", "LOST"}


def test_running_the_seed_twice_writes_nothing_new(db_session: Session) -> None:
    seed.seed()
    before = (counts(db_session), _activity_types(db_session))

    second = seed.seed()

    assert (counts(db_session), _activity_types(db_session)) == before
    assert second["duplicate"] == len(seed.PEOPLE) + len(seed.FOLLOW_UPS)
    assert second["CREATED"] == second["UPDATED"] == second["status_changes"] == 0


def test_seed_refuses_production_unless_explicitly_allowed(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    production = Settings(environment="production", meta_app_secret="s", meta_verify_token="t")
    monkeypatch.setattr(seed, "get_settings", lambda: production)

    assert seed.main([]) == 1
    assert "Refusing to seed production" in capsys.readouterr().err
    assert counts(db_session) == (0, 0, 0)

    assert seed.main(["--allow-production"]) == 0
    assert counts(db_session)[0] == len(seed.PEOPLE)
