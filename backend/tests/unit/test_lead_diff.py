from datetime import UTC, datetime, timedelta, timezone

from app.services.webhook_service import diff_lead_fields

CURRENT = {
    "full_name": "Rahul Sharma",
    "email": "rahul@example.com",
    "phone": "+911",
    "campaign_id": "cmp_a",
    "meta_created_at": datetime(2026, 9, 24, 10, 0, tzinfo=UTC),
}


def test_identical_values_produce_no_changes() -> None:
    assert diff_lead_fields(CURRENT, dict(CURRENT)) == {}


def test_changed_values_are_reported_as_old_and_new() -> None:
    incoming = {**CURRENT, "phone": "+912", "campaign_id": "cmp_b"}

    assert diff_lead_fields(CURRENT, incoming) == {
        "phone": ("+911", "+912"),
        "campaign_id": ("cmp_a", "cmp_b"),
    }


def test_missing_or_null_incoming_values_never_erase_stored_ones() -> None:
    assert diff_lead_fields(CURRENT, {"email": None, "phone": None}) == {}


def test_a_value_for_a_previously_empty_field_is_a_change() -> None:
    assert diff_lead_fields({"email": None}, {"email": "new@example.com"}) == {
        "email": (None, "new@example.com")
    }


def test_status_and_unknown_fields_are_never_diffed() -> None:
    assert diff_lead_fields({"status": "CONTACTED"}, {"status": "NEW", "id": "x"}) == {}


def test_same_instant_in_another_timezone_is_not_a_change() -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    same_instant = datetime(2026, 9, 24, 15, 30, tzinfo=ist)

    assert diff_lead_fields(CURRENT, {"meta_created_at": same_instant}) == {}
