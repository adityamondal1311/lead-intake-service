from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import WebhookEvent


def insert_if_new(
    session: Session, *, source: str, external_event_id: str, payload: dict[str, Any]
) -> WebhookEvent | None:
    """Record a delivery unless the same (source, external_event_id) was already recorded.

    Returns the new row, or None for a duplicate. This is a single
    INSERT ... ON CONFLICT DO NOTHING RETURNING statement, not a SELECT followed by an INSERT:
    a separate existence check leaves a window in which two concurrent deliveries both see
    "not found" and both insert. Here the unique constraint decides. If another transaction
    has inserted the same event but not yet committed, this statement waits for it: on commit
    it becomes a conflict (duplicate); on rollback this insert proceeds, so a failed attempt
    never blocks the retry.
    """
    statement = (
        insert(WebhookEvent)
        .values(source=source, external_event_id=external_event_id, payload=payload)
        .on_conflict_do_nothing(constraint="uq_webhook_events_source_external_event_id")
        .returning(WebhookEvent)
    )
    return session.scalars(statement).one_or_none()
