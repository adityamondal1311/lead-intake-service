import logging
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Activity, Lead, WebhookEvent
from app.models.enums import ActivityType, LeadSource, WebhookOutcome
from app.repositories import activity_repository, lead_repository, webhook_event_repository
from app.schemas.webhook import MetaLeadPayload

logger = logging.getLogger(__name__)

WEBHOOK_ACTOR = "system:meta_webhook"

# Lead attributes a webhook may change, mapped to the name used in LEAD_UPDATED diffs (the
# API's camelCase field names, so the frontend can show them directly). Status is deliberately
# absent: the webhook never changes a lead's status, only the sales team does.
UPDATABLE_FIELDS = {
    "full_name": "fullName",
    "email": "email",
    "phone": "phone",
    "campaign_id": "campaignId",
    "form_id": "formId",
    "ad_id": "adId",
    "meta_created_at": "metaCreatedAt",
}


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
    return {
        "full_name": payload.full_name,
        "email": payload.email,
        "phone": payload.phone,
        "campaign_id": payload.campaign_id,
        "form_id": payload.form_id,
        "ad_id": payload.ad_id,
        "meta_created_at": payload.created_time,
    }


def diff_lead_fields(
    current: Mapping[str, Any], incoming: Mapping[str, Any]
) -> dict[str, tuple[Any, Any]]:
    """Fields whose incoming value differs from the stored one, as {attr: (old, new)}.

    Partial-update semantics: an incoming None (field absent or blank in this event) never
    erases a stored value. A later event may simply not carry every field, and deleting
    known-good contact data because of that would be worse than keeping it.
    """
    return {
        attr: (current.get(attr), new)
        for attr, new in incoming.items()
        if attr in UPDATABLE_FIELDS and new is not None and new != current.get(attr)
    }


def _json_value(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime) else value


def _record_activity(
    session: Session,
    lead: Lead,
    event: WebhookEvent,
    activity_type: ActivityType,
    details: dict[str, Any],
) -> None:
    activity_repository.add(
        session,
        Activity(
            lead_id=lead.id,
            type=activity_type,
            actor=WEBHOOK_ACTOR,
            details={
                **details,
                "webhookEventId": str(event.id),
                "externalEventId": event.external_event_id,
            },
        ),
    )


def _apply_to_lead(
    session: Session, payload: MetaLeadPayload, event: WebhookEvent
) -> tuple[Lead, WebhookOutcome]:
    """Create the lead, or update it from a later event, recording the matching activity."""
    fields = _lead_fields(payload)

    lead = lead_repository.get_by_external_id_for_update(session, payload.lead_id)
    if lead is None:
        lead = lead_repository.insert_if_new(
            session, external_id=payload.lead_id, source=LeadSource.META_ADS, **fields
        )
        if lead is not None:
            _record_activity(
                session, lead, event, ActivityType.LEAD_CREATED, {"source": LeadSource.META_ADS}
            )
            return lead, WebhookOutcome.CREATED
        # Another delivery created this lead between our SELECT and INSERT. ON CONFLICT waited
        # for it to commit, so the row is visible now: lock it and continue as an update.
        lead = lead_repository.get_by_external_id_for_update(session, payload.lead_id)
        if lead is None:  # cannot happen: a conflict means a committed row exists
            raise RuntimeError("lead insert conflicted but the lead is not visible")

    current = {attr: getattr(lead, attr) for attr in UPDATABLE_FIELDS}
    changes = diff_lead_fields(current, fields)
    if not changes:
        return lead, WebhookOutcome.UNCHANGED

    for attr, (_, new) in changes.items():
        setattr(lead, attr, new)
    _record_activity(
        session,
        lead,
        event,
        ActivityType.LEAD_UPDATED,
        {
            "changes": {
                UPDATABLE_FIELDS[attr]: {"from": _json_value(old), "to": _json_value(new)}
                for attr, (old, new) in changes.items()
            }
        },
    )
    return lead, WebhookOutcome.UPDATED


def process_meta_lead(
    session: Session, payload: MetaLeadPayload, raw_payload: dict[str, Any]
) -> WebhookResult:
    """Process one webhook delivery in a single transaction.

    1. Record the delivery with INSERT ... ON CONFLICT DO NOTHING. If the event was already
       recorded it is a duplicate: nothing is written and DUPLICATE is returned.
    2. Lock the lead by Meta lead_id (SELECT ... FOR UPDATE):
       - not found → insert it (race-safe) + LEAD_CREATED            → outcome CREATED
       - found, some incoming field differs → update + LEAD_UPDATED  → outcome UPDATED
       - found, nothing differs → no write, no activity              → outcome UNCHANGED
    3. Mark the delivery processed (lead, outcome, processed_at). The delivery is recorded
       whatever the outcome, including UNCHANGED.

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

            lead, outcome = _apply_to_lead(session, payload, event)

            event.lead_id = lead.id
            event.outcome = outcome
            # Database clock at the end of processing (now() would equal received_at: same txn).
            event.processed_at = func.clock_timestamp()
    except Exception:
        # The request middleware logs the traceback under the same request id; this line ties
        # the failure to the Meta event without logging any lead data.
        logger.warning("webhook processing failed", extra=log_context)
        raise

    logger.info(
        "webhook processed",
        extra={**log_context, "outcome": outcome.value, "lead_id": str(lead.id)},
    )
    return WebhookResult(outcome=outcome, lead_id=lead.id)
