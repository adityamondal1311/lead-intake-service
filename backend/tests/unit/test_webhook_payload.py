from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.webhook import MetaLeadPayload


def _payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "event_id": "evt_1",
        "lead_id": "meta_lead_1",
        "full_name": "Rahul Sharma",
        "email": "rahul@example.com",
        "phone": "+919999999999",
    }
    payload.update(overrides)
    return {k: v for k, v in payload.items() if v is not ...}


def _error_messages(**overrides: Any) -> list[str]:
    with pytest.raises(ValidationError) as exc_info:
        MetaLeadPayload.model_validate(_payload(**overrides))
    return [error["msg"] for error in exc_info.value.errors()]


def test_email_only_and_phone_only_are_both_accepted() -> None:
    assert MetaLeadPayload.model_validate(_payload(phone=...)).phone is None
    assert MetaLeadPayload.model_validate(_payload(email=...)).email is None


def test_a_contact_method_is_required() -> None:
    assert _error_messages(email=..., phone=...) == [
        "Value error, at least one of email or phone is required"
    ]


def test_blank_contact_fields_count_as_missing() -> None:
    assert _error_messages(email="  ", phone="") == [
        "Value error, at least one of email or phone is required"
    ]


@pytest.mark.parametrize("field", ["event_id", "lead_id", "full_name"])
def test_required_identity_fields(field: str) -> None:
    assert _error_messages(**{field: ...}) == ["Field required"]
    assert len(_error_messages(**{field: "   "})) == 1  # whitespace-only is empty


def test_invalid_email_is_rejected() -> None:
    assert len(_error_messages(email="not-an-email")) == 1


def test_values_are_trimmed_and_email_lowercased() -> None:
    payload = MetaLeadPayload.model_validate(
        _payload(full_name="  Rahul Sharma ", email=" Rahul.Sharma@Example.COM ", phone=" +91 99 ")
    )

    assert payload.full_name == "Rahul Sharma"
    assert payload.email == "rahul.sharma@example.com"
    assert payload.phone == "+91 99"


def test_optional_ids_default_to_none_and_blank_becomes_none() -> None:
    payload = MetaLeadPayload.model_validate(_payload(campaign_id="", form_id="  "))

    assert (payload.campaign_id, payload.form_id, payload.ad_id) == (None, None, None)


@pytest.mark.parametrize(
    "created_time",
    ["2026-09-24T10:00:00Z", "2026-09-24T10:00:00+0000", "2026-09-24T15:30:00+05:30"],
)
def test_created_time_accepts_meta_style_timezones(created_time: str) -> None:
    payload = MetaLeadPayload.model_validate(_payload(created_time=created_time))

    assert payload.created_time == datetime(2026, 9, 24, 10, 0, tzinfo=UTC)


def test_created_time_without_timezone_is_rejected() -> None:
    assert len(_error_messages(created_time="2026-09-24T10:00:00")) == 1


def test_unknown_fields_are_ignored() -> None:
    payload = MetaLeadPayload.model_validate(_payload(page_id="p1", custom_question="yes"))

    assert not hasattr(payload, "page_id")


def test_overlong_values_are_rejected() -> None:
    assert len(_error_messages(lead_id="x" * 256)) == 1
    assert len(_error_messages(phone="1" * 33)) == 1
