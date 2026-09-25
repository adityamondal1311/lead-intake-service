import uuid
from typing import Any, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models.enums import WebhookOutcome
from app.schemas.common import CamelModel


class MetaLeadPayload(BaseModel):
    """The normalized lead payload this service accepts at POST /webhook/meta-lead.

    Real Meta Lead Ads webhooks carry only a leadgen_id plus page/form/ad ids; the field data is
    then fetched from the Graph API. This payload represents that lead *after* enrichment; the
    Graph API call is out of scope (see README). Field names are snake_case, as Meta sends them.
    """

    # Unknown fields are ignored so the sender can add fields without breaking ingestion.
    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "event_id": "evt_123",
                    "lead_id": "meta_lead_123",
                    "created_time": "2026-09-24T10:00:00+0000",
                    "campaign_id": "cmp_coworking_delhi",
                    "form_id": "form_workspace_enquiry",
                    "ad_id": "ad_1",
                    "full_name": "Rahul Sharma",
                    "email": "rahul@example.com",
                    "phone": "+919999999999",
                }
            ]
        },
    )

    event_id: str = Field(min_length=1, max_length=255)
    lead_id: str = Field(min_length=1, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=32)
    campaign_id: str | None = Field(default=None, max_length=255)
    form_id: str | None = Field(default=None, max_length=255)
    ad_id: str | None = Field(default=None, max_length=255)
    # Must carry a timezone (e.g. "Z" or "+00:00"), so it is never guessed.
    created_time: AwareDatetime | None = None

    @field_validator("email", "phone", "campaign_id", "form_id", "ad_id", mode="before")
    @classmethod
    def blank_to_none(cls, value: Any) -> Any:
        # Form tools often send "" for unanswered fields; treat that as not provided.
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str | None) -> str | None:
        return value.lower() if value else value

    @model_validator(mode="after")
    def require_a_contact_method(self) -> Self:
        if not self.email and not self.phone:
            raise ValueError("at least one of email or phone is required")
        return self


class WebhookAck(CamelModel):
    """Response to Meta. Any 2xx tells Meta the delivery was received and must not be retried."""

    status: Literal["processed", "duplicate"]
    outcome: WebhookOutcome | None = None
    lead_id: uuid.UUID | None = None
