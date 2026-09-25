import uuid
from datetime import datetime

from app.models.enums import LeadStatus
from app.schemas.activity import ActivityRead
from app.schemas.common import CamelModel, Pagination


class LeadSummary(CamelModel):
    """A row in the lead list."""

    id: uuid.UUID
    full_name: str
    email: str | None
    phone: str | None
    status: LeadStatus
    source: str
    campaign_id: str | None
    created_at: datetime


class LeadDetail(LeadSummary):
    external_id: str
    form_id: str | None
    ad_id: str | None
    meta_created_at: datetime | None
    updated_at: datetime


class LeadListResponse(CamelModel):
    data: list[LeadSummary]
    pagination: Pagination


class LeadDetailResponse(CamelModel):
    lead: LeadDetail
    activities: list[ActivityRead]  # newest first


class LeadStatusUpdate(CamelModel):
    status: LeadStatus


class LeadStatusUpdateResponse(CamelModel):
    lead: LeadDetail
    # The STATUS_CHANGED activity that was recorded; null when the lead already had this status.
    activity: ActivityRead | None
