import uuid

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.models import Lead
from app.models.enums import LeadStatus


def _escape_like(term: str) -> str:
    """Make % and _ in user input match literally instead of acting as LIKE wildcards."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _list_filters(status: LeadStatus | None, search: str | None) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []
    if status is not None:
        filters.append(Lead.status == status)
    if search:
        # Case-insensitive substring match. Unindexed ILIKE is fine at this scale; a pg_trgm GIN
        # index is the scaling path.
        pattern = f"%{_escape_like(search)}%"
        filters.append(
            or_(
                Lead.full_name.ilike(pattern, escape="\\"),
                Lead.email.ilike(pattern, escape="\\"),
                Lead.phone.ilike(pattern, escape="\\"),
            )
        )
    return filters


def list_leads(
    session: Session,
    *,
    status: LeadStatus | None,
    search: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Lead], int]:
    """One page of leads, newest first, plus the total number of matching leads."""
    filters = _list_filters(status, search)
    total = session.scalar(select(func.count()).select_from(Lead).where(*filters)) or 0
    leads = session.scalars(
        select(Lead)
        .where(*filters)
        # id breaks ties between equal timestamps, so page boundaries are stable.
        .order_by(Lead.created_at.desc(), Lead.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(leads), total


def get_by_id(session: Session, lead_id: uuid.UUID) -> Lead | None:
    return session.get(Lead, lead_id)


def get_by_id_for_update(session: Session, lead_id: uuid.UUID) -> Lead | None:
    """Load a lead and lock its row (SELECT ... FOR UPDATE) until the transaction ends.

    A concurrent transaction that wants the same row waits here, so read-modify-write sequences
    on one lead are serialized. populate_existing makes the ORM overwrite any copy of this lead
    already in the session with the values read under the lock, instead of keeping stale ones.
    """
    return session.scalars(
        select(Lead)
        .where(Lead.id == lead_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()
