import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ActivityType, in_values


class Activity(Base):
    """Audit trail entry. Append-only: the application never updates or deletes activities."""

    __tablename__ = "activities"
    __table_args__ = (CheckConstraint(in_values("type", ActivityType), name="type"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # CASCADE: activities have no meaning without their lead, so deleting a lead (e.g. a GDPR
    # erasure request) removes its history too.
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(32))
    # Who caused it, e.g. "system:meta_webhook" or "user:dashboard".
    actor: Mapped[str] = mapped_column(String(64))
    # Type-specific data (status from/to, field diff, webhook event ids). Not named `metadata`:
    # that attribute name is reserved by SQLAlchemy's declarative base.
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Activity timeline for one lead, newest first: WHERE lead_id = ? ORDER BY created_at DESC.
# Leading with lead_id also serves the foreign key (Postgres does not index FKs automatically).
Index("ix_activities_lead_id_created_at", Activity.lead_id, Activity.created_at.desc())
