"""activities created_at uses clock_timestamp

Revision ID: 315288742ea3
Revises: bc56044ea24c
Create Date: 2026-09-25 19:17:54.607993

now() is the transaction start time. Under concurrent status changes, a transaction that waited
on the lead's row lock can have started before the one it waited for, so its activity sorted
earlier on the timeline than the change it followed. clock_timestamp() is evaluated at INSERT
time (after the lock is held), so activity order matches the real order of changes.
Only the column default changes; existing rows are untouched.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "315288742ea3"
down_revision: str | Sequence[str] | None = "bc56044ea24c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("activities", "created_at", server_default=sa.text("clock_timestamp()"))


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("activities", "created_at", server_default=sa.text("now()"))
