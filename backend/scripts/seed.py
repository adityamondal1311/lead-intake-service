"""Seed demo leads through the application's own services (no direct SQL inserts).

Every lead arrives as a Meta webhook payload, validated by MetaLeadPayload and processed by
webhook_service exactly like a real delivery, so it gets its webhook_events row and LEAD_CREATED
activity. A few leads receive a second event (LEAD_UPDATED, or UNCHANGED for identical data),
and status changes go through lead_service.update_status (STATUS_CHANGED). The demo data is
therefore a real run of the system, with a genuine audit trail.

Idempotent: event ids are fixed, so running it again finds every delivery already recorded
(duplicate) and writes nothing. Status history is applied only to leads created by the current
run, so a re-run never replays status changes.

Usage (from backend/, with the database migrated):
    uv run python -m scripts.seed
    uv run python -m scripts.seed --allow-production   # only if you really mean it
"""

import argparse
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.enums import LeadStatus, WebhookOutcome
from app.schemas.webhook import MetaLeadPayload
from app.services import lead_service, webhook_service

# Fixed reference time, so payloads (and therefore re-runs) are identical.
SEED_TIME = datetime(2026, 9, 20, 9, 0, tzinfo=UTC)

CAMPAIGNS = ["cmp_coworking_delhi", "cmp_flexi_desk_bengaluru", "cmp_meeting_rooms_mumbai"]

# name, email?, phone?  (a few leads have only one contact method, as real forms allow)
PEOPLE: list[tuple[str, str | None, str | None]] = [
    ("Rahul Sharma", "rahul.sharma@example.com", "+919810000001"),
    ("Priya Patel", "priya.patel@example.com", "+919810000002"),
    ("Amit Kumar", "amit.kumar@example.com", None),
    ("Sneha Iyer", "sneha.iyer@example.com", "+919810000004"),
    ("Vikram Singh", None, "+919810000005"),
    ("Ananya Reddy", "ananya.reddy@example.com", "+919810000006"),
    ("Rohan Mehta", "rohan.mehta@example.com", "+919810000007"),
    ("Kavya Nair", "kavya.nair@example.com", "+919810000008"),
    ("Arjun Das", "arjun.das@example.com", None),
    ("Meera Joshi", "meera.joshi@example.com", "+919810000010"),
    ("Karan Malhotra", None, "+919810000011"),
    ("Divya Menon", "divya.menon@example.com", "+919810000012"),
    ("Siddharth Rao", "siddharth.rao@example.com", "+919810000013"),
    ("Neha Gupta", "neha.gupta@example.com", "+919810000014"),
    ("Aditya Verma", "aditya.verma@example.com", "+919810000015"),
    ("Pooja Kulkarni", "pooja.kulkarni@example.com", None),
    ("Nikhil Bansal", "nikhil.bansal@example.com", "+919810000017"),
    ("Isha Chatterjee", "isha.chatterjee@example.com", "+919810000018"),
    ("Manish Agarwal", None, "+919810000019"),
    ("Riya Kapoor", "riya.kapoor@example.com", "+919810000020"),
    ("Harsh Vardhan", "harsh.vardhan@example.com", "+919810000021"),
    ("Tanvi Deshpande", "tanvi.deshpande@example.com", "+919810000022"),
    ("Gaurav Saxena", "gaurav.saxena@example.com", "+919810000023"),
    ("Shreya Pillai", "shreya.pillai@example.com", "+919810000024"),
    ("Varun Chopra", "varun.chopra@example.com", "+919810000025"),
]

# Status histories, cycled over the leads (applied in order through the status service).
S = LeadStatus
STATUS_PATHS: list[list[LeadStatus]] = [
    [],
    [S.CONTACTED],
    [S.CONTACTED, S.QUALIFIED],
    [S.CONTACTED, S.QUALIFIED, S.CONVERTED],
    [S.CONTACTED, S.LOST],
    [],
    [S.LOST],
    [S.CONTACTED, S.QUALIFIED, S.LOST, S.QUALIFIED],  # a lost lead reopened
]

# Leads that receive a second event: index -> changed fields (empty = identical → UNCHANGED).
FOLLOW_UPS: dict[int, dict[str, Any]] = {
    0: {"phone": "+919820000001"},
    3: {"campaign_id": CAMPAIGNS[2]},
    6: {"email": "rohan.m@example.com", "phone": "+919820000007"},
    9: {},
    12: {"full_name": "Siddharth R. Rao"},
}


def _lead_payload(index: int, event_suffix: str, **changes: Any) -> dict[str, Any]:
    name, email, phone = PEOPLE[index]
    payload: dict[str, Any] = {
        "event_id": f"seed_evt_{index + 1:03d}{event_suffix}",
        "lead_id": f"seed_lead_{index + 1:03d}",
        "created_time": (SEED_TIME - timedelta(hours=7 * index)).isoformat(),
        "campaign_id": CAMPAIGNS[index % len(CAMPAIGNS)],
        "form_id": "form_workspace_enquiry",
        "ad_id": f"ad_{index % 4 + 1}",
        "full_name": name,
    }
    if email:
        payload["email"] = email
    if phone:
        payload["phone"] = phone
    payload.update(changes)
    return payload


def _deliver(raw: dict[str, Any]) -> webhook_service.WebhookResult:
    payload = MetaLeadPayload.model_validate(raw)  # same validation as the HTTP endpoint
    with SessionLocal() as session:
        return webhook_service.process_meta_lead(session, payload, raw)


def _label(result: webhook_service.WebhookResult) -> str:
    return "duplicate" if result.outcome is None else result.outcome.value


def seed() -> Counter[str]:
    """Run the seed; returns counts of what happened (for the summary and for tests)."""
    tally: Counter[str] = Counter()
    for index in range(len(PEOPLE)):
        created = _deliver(_lead_payload(index, ""))
        tally[_label(created)] += 1

        if index in FOLLOW_UPS:
            follow_up = _deliver(_lead_payload(index, "_b", **FOLLOW_UPS[index]))
            tally[_label(follow_up)] += 1

        # Only for leads created by this run, so a re-run never replays status history.
        if created.outcome == WebhookOutcome.CREATED and created.lead_id is not None:
            for status in STATUS_PATHS[index % len(STATUS_PATHS)]:
                with SessionLocal() as session:
                    _, activity = lead_service.update_status(session, created.lead_id, status)
                tally["status_changes"] += activity is not None
    return tally


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed demo leads through the real services.")
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Permit seeding when ENVIRONMENT=production",
    )
    args = parser.parse_args(argv)

    if get_settings().environment == "production" and not args.allow_production:
        print(
            "Refusing to seed production. Use --allow-production only if this is intentional.",
            file=sys.stderr,
        )
        return 1

    tally = seed()
    print(
        "Seed complete: "
        f"{tally['CREATED']} created, {tally['UPDATED']} updated, {tally['UNCHANGED']} unchanged, "
        f"{tally['duplicate']} duplicate deliveries, {tally['status_changes']} status changes."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
