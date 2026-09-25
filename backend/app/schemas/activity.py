import uuid
from datetime import datetime
from typing import Any

from app.models.enums import ActivityType
from app.schemas.common import CamelModel


class ActivityRead(CamelModel):
    id: uuid.UUID
    type: ActivityType
    actor: str
    details: dict[str, Any]
    created_at: datetime
