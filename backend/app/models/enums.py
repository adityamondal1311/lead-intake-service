from enum import StrEnum


class LeadStatus(StrEnum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    CONVERTED = "CONVERTED"
    LOST = "LOST"


class LeadSource(StrEnum):
    META_ADS = "META_ADS"


class ActivityType(StrEnum):
    LEAD_CREATED = "LEAD_CREATED"
    LEAD_UPDATED = "LEAD_UPDATED"
    STATUS_CHANGED = "STATUS_CHANGED"


class WebhookOutcome(StrEnum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    UNCHANGED = "UNCHANGED"


def in_values(column: str, enum: type[StrEnum]) -> str:
    """SQL for a CHECK constraint limiting `column` to the enum's values.

    Enums are stored as VARCHAR + CHECK rather than native Postgres ENUM types: adding a value
    to a native ENUM needs special migration handling, while a CHECK is a plain drop-and-recreate.
    Generating the CHECK from the Python enum keeps code and database in step.
    """
    values = ", ".join(f"'{member.value}'" for member in enum)
    return f"{column} IN ({values})"
