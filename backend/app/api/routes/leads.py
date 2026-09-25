import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.enums import LeadStatus
from app.schemas.activity import ActivityRead
from app.schemas.common import ErrorResponse, Pagination
from app.schemas.lead import LeadDetail, LeadDetailResponse, LeadListResponse, LeadSummary
from app.services import lead_service

router = APIRouter(prefix="/leads", tags=["leads"])

DbSession = Annotated[Session, Depends(get_db)]

_VALIDATION_ERROR = {422: {"model": ErrorResponse, "description": "Invalid parameters"}}
_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Lead not found"}}


@router.get(
    "",
    summary="List leads",
    description="Newest first. Filter by status, search name/email/phone (case-insensitive "
    "substring), paginate with page/limit. A page past the end returns an empty `data` list.",
    responses=_VALIDATION_ERROR,
)
def list_leads(
    db: DbSession,
    page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    status: Annotated[LeadStatus | None, Query(description="Only leads in this status")] = None,
    search: Annotated[
        str | None, Query(max_length=100, description="Matches name, email or phone")
    ] = None,
) -> LeadListResponse:
    result = lead_service.list_leads(db, page=page, limit=limit, status=status, search=search)
    return LeadListResponse(
        data=[LeadSummary.model_validate(lead) for lead in result.leads],
        pagination=Pagination(
            page=result.page,
            limit=result.limit,
            total=result.total,
            total_pages=result.total_pages,
        ),
    )


@router.get(
    "/{lead_id}",
    summary="Get a lead with its activity timeline",
    description="Returns the lead and its activities, newest first.",
    responses={**_NOT_FOUND, **_VALIDATION_ERROR},
)
def get_lead(db: DbSession, lead_id: uuid.UUID) -> LeadDetailResponse:
    lead, activities = lead_service.get_lead_with_activities(db, lead_id)
    return LeadDetailResponse(
        lead=LeadDetail.model_validate(lead),
        activities=[ActivityRead.model_validate(activity) for activity in activities],
    )
