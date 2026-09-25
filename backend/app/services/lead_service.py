import math
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.errors import LeadNotFoundError
from app.models import Activity, Lead
from app.models.enums import LeadStatus
from app.repositories import activity_repository, lead_repository


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
