import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Activity


def list_for_lead(session: Session, lead_id: uuid.UUID) -> list[Activity]:
    """A lead's timeline, newest first (served by ix_activities_lead_id_created_at)."""
    activities = session.scalars(
        select(Activity)
        .where(Activity.lead_id == lead_id)
        .order_by(Activity.created_at.desc(), Activity.id.desc())
    ).all()
    return list(activities)


def add(session: Session, activity: Activity) -> Activity:
    """Append an activity. There is deliberately no update or delete: the audit trail is
    append-only."""
    session.add(activity)
    return activity
