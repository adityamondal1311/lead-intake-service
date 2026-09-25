from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base for API schemas: snake_case in Python, camelCase in JSON (the frontend's convention).

    Accepts both spellings on input, always emits camelCase, and can be built directly from ORM
    objects.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        from_attributes=True,
    )


class Pagination(CamelModel):
    page: int
    limit: int
    total: int
    total_pages: int


class ErrorBody(CamelModel):
    code: str
    message: str
    details: Any = None
    request_id: str | None = None


class ErrorResponse(CamelModel):
    """Envelope for every non-2xx response."""

    error: ErrorBody
