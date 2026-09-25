# Importing the models registers their tables on Base.metadata. Alembic autogenerate and the test
# suite import this package so they always see every table.
from app.models.activity import Activity
from app.models.lead import Lead
from app.models.webhook_event import WebhookEvent

__all__ = ["Activity", "Lead", "WebhookEvent"]
