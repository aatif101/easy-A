"""create section rankings cache

Revision ID: 0003_create_section_rankings
Revises: 0002_create_section_syllabus_tables
Create Date: 2026-09-20 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_create_section_rankings"
down_revision: str | None = "0002_create_section_syllabus_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "section_rankings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(length=6), nullable=False),
        sa.Column("term_name", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=16), nullable=False),
        sa.Column("course_number", sa.String(length=16), nullable=False),
        sa.Column("crn", sa.String(length=16), nullable=False),
        sa.Column("course_title", sa.String(length=255), nullable=False),
        sa.Column("instructor", sa.String(length=255), nullable=True),
        sa.Column("easiness_score", sa.Float(), nullable=False),
        sa.Column("smoothed_withdrawal_rate", sa.Float(), nullable=False),
        sa.Column("confidence_label", sa.String(length=16), nullable=False),
        sa.Column("score_source", sa.String(length=32), nullable=False),
        sa.Column("effective_n", sa.Float(), nullable=False),
        sa.Column("delivery_method", sa.String(length=32), nullable=True),
        sa.Column("historical_analytics", sa.JSON(), nullable=False),
        sa.Column("gened_attributes", sa.JSON(), nullable=False),
        sa.Column("signals", sa.JSON(), nullable=False),
        sa.Column("instructor_provenance", sa.JSON(), nullable=False),
        sa.Column("gened_provenance", sa.JSON(), nullable=False),
        sa.Column("signal_provenance", sa.JSON(), nullable=False),
        sa.Column("section_provenance", sa.JSON(), nullable=False),
        sa.Column("modality", sa.JSON(), nullable=False),
        sa.Column(
            "refreshed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            name=op.f("fk_section_rankings_section_id_sections"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_section_rankings")),
        sa.UniqueConstraint("section_id", name=op.f("uq_section_rankings_section_id")),
    )
    for column_name in (
        "easiness_score",
        "smoothed_withdrawal_rate",
        "confidence_label",
        "subject",
        "course_number",
        "delivery_method",
    ):
        op.create_index(
            op.f(f"ix_section_rankings_{column_name}"),
            "section_rankings",
            [column_name],
            unique=False,
        )


def downgrade() -> None:
    op.drop_table("section_rankings")
