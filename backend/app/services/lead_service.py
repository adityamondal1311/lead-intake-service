import math
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.errors import LeadNotFoundError
from app.models import Activity, Lead
from app.models.enums import ActivityType, LeadStatus
from app.repositories import activity_repository, lead_repository

# Recorded as the activity actor for changes made through the dashboard API. With no auth yet
# there is no individual user to attribute; with auth this becomes "user:<id>".
DASHBOARD_ACTOR = "user:dashboard"


@dataclass(frozen=True)
class LeadPage:
    leads: list[Lead]
    page: int
    limit: int
    total: int

    @property
    def total_pages(self) -> int:
        return math.ceil(self.total / self.limit)


def list_leads(
    session: Session,
    *,
    page: int,
    limit: int,
    status: LeadStatus | None = None,
    search: str | None = None,
) -> LeadPage:
    # Blank or whitespace-only search means "no search", not "match nothing".
    search = search.strip() if search else None
    leads, total = lead_repository.list_leads(
        session, status=status, search=search or None, limit=limit, offset=(page - 1) * limit
    )
    # A page past the end returns an empty list with correct totals rather than an error, so
    # a client holding a stale page number (e.g. after leads were filtered away) recovers.
    return LeadPage(leads=leads, page=page, limit=limit, total=total)


def get_lead_with_activities(session: Session, lead_id: uuid.UUID) -> tuple[Lead, list[Activity]]:
    lead = lead_repository.get_by_id(session, lead_id)
    if lead is None:
        raise LeadNotFoundError()
    return lead, activity_repository.list_for_lead(session, lead_id)


def update_status(
    session: Session, lead_id: uuid.UUID, new_status: LeadStatus
) -> tuple[Lead, Activity | None]:
    """Change a lead's status and record a STATUS_CHANGED activity, atomically.

    Both writes happen in one transaction: if the activity insert fails, the status change is
    rolled back too, so a lead and its audit trail can never disagree. The row lock makes the
    recorded "from" value correct even when two users change the same lead at once: the second
    waits for the first to commit and then reads the status the first one set.

    Setting the status the lead already has is a no-op: nothing is written and no activity is
    recorded, which keeps the audit trail free of noise. Returns (lead, None) in that case.
    """
    with session.begin():
        lead = lead_repository.get_by_id_for_update(session, lead_id)
        if lead is None:
            raise LeadNotFoundError()
        if lead.status == new_status:
            return lead, None

        previous_status = lead.status
        lead.status = new_status
        activity = activity_repository.add(
            session,
            Activity(
                lead_id=lead.id,
                type=ActivityType.STATUS_CHANGED,
                actor=DASHBOARD_ACTOR,
                details={"from": previous_status, "to": new_status.value},
            ),
        )
    return lead, activity
