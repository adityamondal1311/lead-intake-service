import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import LeadSource, LeadStatus, in_values


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (CheckConstraint(in_values("status", LeadStatus), name="status"),)
    # Fetch server-generated values (created_at, updated_at) via RETURNING on INSERT and UPDATE,
    # so they are populated on the object without an extra SELECT.
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Meta's lead_id: the lead's identity. UNIQUE, so a lead can never be stored twice.
    external_id: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320))  # RFC 5321 maximum length
    phone: Mapped[str | None] = mapped_column(String(32))  # string: keeps "+" and leading zeros
    source: Mapped[str] = mapped_column(
        String(32), default=LeadSource.META_ADS, server_default=LeadSource.META_ADS
    )
    campaign_id: Mapped[str | None] = mapped_column(String(255))
    form_id: Mapped[str | None] = mapped_column(String(255))
    ad_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(20), default=LeadStatus.NEW, server_default=LeadStatus.NEW
    )
    # When the lead was submitted on Meta (payload created_time), as opposed to when we stored it.
    meta_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# Lead list filtered by status, newest first: WHERE status = ? ORDER BY created_at DESC.
Index("ix_leads_status_created_at", Lead.status, Lead.created_at.desc())
# Unfiltered lead list, newest first: ORDER BY created_at DESC.
Index("ix_leads_created_at", Lead.created_at.desc())
