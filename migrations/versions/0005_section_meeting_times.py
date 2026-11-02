"""add sections.meeting_times, the schedule's raw TIME cell

Manual apply only: the operator applies this to hosted Supabase BEFORE deploying the code that
reads it. The column is nullable and stays empty until the next sync sweep fills it. The downgrade
discards only the stored cells; a sweep after the next upgrade restores them.

Revision ID: 0005_section_meeting_times
Revises: 0004_sync_removed_at
Create Date: 2026-11-02 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_section_meeting_times"
down_revision: str | None = "0004_sync_removed_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sections", sa.Column("meeting_times", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sections", "meeting_times")
