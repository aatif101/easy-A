"""add sections.removed_at and the seat snapshot latest-snapshot index

Manual apply only: the operator applies this to hosted Supabase (plan 09-14). The
downgrade discards every removal mark and makes removed sections searchable again.

Revision ID: 0004_sync_removed_at
Revises: 0003_create_section_rankings
Create Date: 2026-09-29 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_sync_removed_at"
down_revision: str | None = "0003_create_section_rankings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEAT_SNAPSHOT_INDEX = "ix_seat_snapshots_section_id_observed_at"


def upgrade() -> None:
    op.add_column(
        "sections",
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        SEAT_SNAPSHOT_INDEX,
        "seat_snapshots",
        ["section_id", sa.text("observed_at DESC"), sa.text("id DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(SEAT_SNAPSHOT_INDEX, table_name="seat_snapshots")
    op.drop_column("sections", "removed_at")
