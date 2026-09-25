import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Activity, Lead, WebhookEvent
from app.models.enums import ActivityType, LeadSource, WebhookOutcome
from app.repositories import activity_repository, lead_repository, webhook_event_repository
from app.schemas.webhook import MetaLeadPayload

logger = logging.getLogger(__name__)

WEBHOOK_ACTOR = "system:meta_webhook"


@dataclass(frozen=True)
class WebhookResult:
    outcome: WebhookOutcome
    lead_id: uuid.UUID


def _lead_fields(payload: MetaLeadPayload) -> dict[str, Any]:
    """The lead columns a Meta payload populates. Status is never among them: the webhook does
    not change a lead's status, only the sales team does."""
    return {
        "full_name": payload.full_name,
        "email": payload.email,
        "phone": payload.phone,
        "campaign_id": payload.campaign_id,
        "form_id": payload.form_id,
        "ad_id": payload.ad_id,
        "meta_created_at": payload.created_time,
    }


def process_meta_lead(
    session: Session, payload: MetaLeadPayload, raw_payload: dict[str, Any]
) -> WebhookResult:
    """Store the delivery, create the lead and its LEAD_CREATED activity in one transaction.

    Everything commits together or not at all. If any step fails, the webhook_events row is
    rolled back too, so Meta's retry of the same event is processed from a clean slate.

    Handles new leads only. A redelivered event or a new event for an existing lead is rejected
    by the database's unique constraints (no duplicate data can be stored); turning those cases
    into proper duplicate/update handling is the idempotency step that follows.
    """
    log_context = {"event_id": payload.event_id}  # identifiers only, never lead PII
    try:
        with session.begin():
            event = webhook_event_repository.add(
                session,
                WebhookEvent(
                    source=LeadSource.META_ADS,
                    external_event_id=payload.event_id,
                    payload=raw_payload,
                ),
            )
            lead = lead_repository.add(
                session,
                Lead(
                    external_id=payload.lead_id, source=LeadSource.META_ADS, **_lead_fields(payload)
                ),
            )
            # Flush sends the INSERTs so the database enforces its constraints now and the
            # generated ids exist before the activity references them.
            session.flush()
            activity_repository.add(
                session,
                Activity(
                    lead_id=lead.id,
                    type=ActivityType.LEAD_CREATED,
                    actor=WEBHOOK_ACTOR,
                    details={
                        "source": LeadSource.META_ADS.value,
                        "webhookEventId": str(event.id),
                        "externalEventId": payload.event_id,
                    },
                ),
            )
            event.lead_id = lead.id
            event.outcome = WebhookOutcome.CREATED
            # Database clock at the end of processing (now() would equal received_at: same txn).
            event.processed_at = func.clock_timestamp()
    except Exception:
        # The request middleware logs the traceback under the same request id; this line ties
        # the failure to the Meta event without logging any lead data.
        logger.warning("webhook processing failed", extra=log_context)
        raise

    logger.info(
        "webhook processed",
        extra={**log_context, "outcome": WebhookOutcome.CREATED.value, "lead_id": str(lead.id)},
    )
    return WebhookResult(outcome=WebhookOutcome.CREATED, lead_id=lead.id)
