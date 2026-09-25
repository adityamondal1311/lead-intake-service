import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Service and database health",
    description="Runs `SELECT 1`. Returns 503 when the database is unreachable, so a load "
    "balancer or platform health check can tell the process is up but cannot serve requests.",
    responses={503: {"model": HealthResponse, "description": "Database unreachable"}},
)
def health(db: Annotated[Session, Depends(get_db)], response: Response) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("database health check failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="error", database="error")
    return HealthResponse(status="ok", database="ok")
