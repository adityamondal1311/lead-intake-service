import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import WebhookOutcome, in_values


class WebhookEvent(Base):
    """One row per accepted webhook delivery; the basis of delivery idempotency."""

    __tablename__ = "webhook_events"
    __table_args__ = (
        # The idempotency guard: a redelivered event_id cannot be inserted twice, even when two
        # deliveries race. The webhook relies on INSERT ... ON CONFLICT against this constraint.
        UniqueConstraint("source", "external_event_id"),
        CheckConstraint(in_values("outcome", WebhookOutcome), name="outcome"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(32))
    external_event_id: Mapped[str] = mapped_column(String(255))
    # Raw payload, kept for audit and replay. Never returned by the lead APIs and never logged.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # SET NULL: deleting a lead keeps the record that the delivery was received.
    lead_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"))
    # NULL until processing finishes in the same transaction; CHECK allows NULL.
    outcome: Mapped[str | None] = mapped_column(String(16))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
