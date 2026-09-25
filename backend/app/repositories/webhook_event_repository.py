from sqlalchemy.orm import Session

from app.models import WebhookEvent


def add(session: Session, event: WebhookEvent) -> WebhookEvent:
    """Record a received delivery. The UNIQUE (source, external_event_id) constraint rejects a
    second insert of the same delivery."""
    session.add(event)
    return event
