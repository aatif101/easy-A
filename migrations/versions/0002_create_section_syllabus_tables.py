"""create section and syllabus tables

Revision ID: 0002_create_section_syllabus_tables
Revises: 0001_create_data_core
Create Date: 2026-09-01 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_create_section_syllabus_tables"
down_revision: str | None = "0001_create_data_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column(
            "alembic_version",
            "version_num",
            existing_type=sa.String(length=32),
            type_=sa.String(length=64),
            existing_nullable=False,
        )
    op.drop_column("grade_distributions", "section_id")
    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("term_id", sa.Integer(), nullable=False),
        sa.Column("crn", sa.String(length=16), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("section_number", sa.String(length=32), nullable=False),
        sa.Column("campus", sa.String(length=128), nullable=False),
        sa.Column("session", sa.String(length=128), nullable=False),
        sa.Column("section_type", sa.String(length=128), nullable=False),
        sa.Column("credits", sa.String(length=32), nullable=True),
        sa.Column("primary_status", sa.String(length=32), nullable=False),
        sa.Column("secondary_status", sa.String(length=32), nullable=True),
        sa.Column("delivery_method", sa.String(length=32), nullable=True),
        sa.Column("days", sa.String(length=32), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("building", sa.String(length=64), nullable=True),
        sa.Column("room", sa.String(length=64), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("enrollment", sa.Integer(), nullable=True),
        sa.Column("seats_remaining", sa.Integer(), nullable=True),
        sa.Column("wait_seats_available", sa.Integer(), nullable=True),
        sa.Column("section_note", sa.Text(), nullable=True),
        sa.Column("fees_raw", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_sections_course_id_courses"),
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            name=op.f("fk_sections_term_id_terms"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sections")),
        sa.UniqueConstraint("term_id", "crn", name="uq_sections_term_crn"),
    )
    op.create_table(
        "section_instructors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("name_raw", sa.String(length=255), nullable=False),
        sa.Column("name_normalized", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            name=op.f("fk_section_instructors_section_id_sections"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_section_instructors")),
    )
    op.create_table(
        "seat_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("enrollment", sa.Integer(), nullable=True),
        sa.Column("seats_remaining", sa.Integer(), nullable=True),
        sa.Column("wait_seats_available", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            name=op.f("fk_seat_snapshots_section_id_sections"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_seat_snapshots")),
    )
    op.create_table(
        "syllabi",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=True),
        sa.Column("term_id", sa.Integer(), nullable=False),
        sa.Column("crn", sa.String(length=16), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("section_number", sa.String(length=32), nullable=False),
        sa.Column("instructor_raw", sa.String(length=255), nullable=True),
        sa.Column("organization", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("view_url", sa.Text(), nullable=False),
        sa.Column("print_url", sa.Text(), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_syllabi_course_id_courses"),
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            name=op.f("fk_syllabi_section_id_sections"),
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            name=op.f("fk_syllabi_term_id_terms"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_syllabi")),
        sa.UniqueConstraint("document_id", name=op.f("uq_syllabi_document_id")),
    )


def downgrade() -> None:
    op.drop_table("syllabi")
    op.drop_table("seat_snapshots")
    op.drop_table("section_instructors")
    op.drop_table("sections")
    op.add_column("grade_distributions", sa.Column("section_id", sa.Integer(), nullable=True))
