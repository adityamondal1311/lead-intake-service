import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Activity, Lead
from app.models.enums import ActivityType, LeadSource, WebhookOutcome
from app.repositories import activity_repository, lead_repository, webhook_event_repository
from app.schemas.webhook import MetaLeadPayload

logger = logging.getLogger(__name__)

WEBHOOK_ACTOR = "system:meta_webhook"


@dataclass(frozen=True)
class WebhookResult:
    # None means the delivery was a duplicate and nothing was processed.
    outcome: WebhookOutcome | None
    lead_id: uuid.UUID | None = None

    @property
    def is_duplicate(self) -> bool:
        return self.outcome is None


DUPLICATE = WebhookResult(outcome=None)


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
    """Process one webhook delivery in a single transaction.

    1. Record the delivery with INSERT ... ON CONFLICT DO NOTHING. If the same event was already
       recorded, it is a duplicate: nothing is written and DUPLICATE is returned.
    2. Create the lead and its LEAD_CREATED activity, then mark the delivery processed.

    Everything commits together or not at all. If any step fails, the delivery row is rolled
    back too, so Meta's retry of the same event is processed from a clean slate.
    """
    log_context = {"event_id": payload.event_id}  # identifiers only, never lead PII
    try:
        with session.begin():
            event = webhook_event_repository.insert_if_new(
                session,
                source=LeadSource.META_ADS,
                external_event_id=payload.event_id,
                payload=raw_payload,
            )
            if event is None:
                logger.info("webhook duplicate ignored", extra=log_context)
                return DUPLICATE

            lead = lead_repository.add(
                session,
                Lead(
                    external_id=payload.lead_id, source=LeadSource.META_ADS, **_lead_fields(payload)
                ),
            )
            # Flush sends the INSERT so the database enforces its constraints now and the
            # generated id exists before the activity references it.
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
