"""create data core tables

Revision ID: 0001_create_data_core
Revises:
Create Date: 2026-08-31 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_create_data_core"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "terms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("banner_code", sa.String(length=6), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_terms")),
        sa.UniqueConstraint("banner_code", name=op.f("uq_terms_banner_code")),
    )
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=16), nullable=False),
        sa.Column("number", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("credits", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("prerequisites", sa.Text(), nullable=True),
        sa.Column("other_information", sa.Text(), nullable=True),
        sa.Column("catalog_edition", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
        sa.UniqueConstraint("subject", "number", "catalog_edition", name="uq_courses_identity"),
    )
    op.create_table(
        "ingest_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("records_seen", sa.Integer(), nullable=False),
        sa.Column("records_inserted", sa.Integer(), nullable=False),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("records_failed", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingest_runs")),
    )
    op.create_table(
        "course_attributes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("attribute_code", sa.String(length=32), nullable=False),
        sa.Column("attribute_label", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_course_attributes_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_attributes")),
    )
    op.create_table(
        "grade_distributions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("term_id", sa.Integer(), nullable=False),
        sa.Column("crn", sa.String(length=16), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=True),
        sa.Column("section_id", sa.Integer(), nullable=True),
        sa.Column("section_number_raw", sa.String(length=32), nullable=False),
        sa.Column("section_suffix_raw", sa.String(length=32), nullable=True),
        sa.Column("campus_raw", sa.String(length=255), nullable=True),
        sa.Column("a_count", sa.Integer(), nullable=False),
        sa.Column("b_count", sa.Integer(), nullable=False),
        sa.Column("c_count", sa.Integer(), nullable=False),
        sa.Column("d_count", sa.Integer(), nullable=False),
        sa.Column("f_count", sa.Integer(), nullable=False),
        sa.Column("i_count", sa.Integer(), nullable=False),
        sa.Column("s_count", sa.Integer(), nullable=False),
        sa.Column("u_count", sa.Integer(), nullable=False),
        sa.Column("w_count", sa.Integer(), nullable=False),
        sa.Column("other_count", sa.Integer(), nullable=False),
        sa.Column("total_grades", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("a_count >= 0", name=op.f("ck_grade_distributions_a_count_nonnegative")),
        sa.CheckConstraint("b_count >= 0", name=op.f("ck_grade_distributions_b_count_nonnegative")),
        sa.CheckConstraint("c_count >= 0", name=op.f("ck_grade_distributions_c_count_nonnegative")),
        sa.CheckConstraint("d_count >= 0", name=op.f("ck_grade_distributions_d_count_nonnegative")),
        sa.CheckConstraint("f_count >= 0", name=op.f("ck_grade_distributions_f_count_nonnegative")),
        sa.CheckConstraint("i_count >= 0", name=op.f("ck_grade_distributions_i_count_nonnegative")),
        sa.CheckConstraint("s_count >= 0", name=op.f("ck_grade_distributions_s_count_nonnegative")),
        sa.CheckConstraint("u_count >= 0", name=op.f("ck_grade_distributions_u_count_nonnegative")),
        sa.CheckConstraint("w_count >= 0", name=op.f("ck_grade_distributions_w_count_nonnegative")),
        sa.CheckConstraint(
            "other_count >= 0",
            name=op.f("ck_grade_distributions_other_count_nonnegative"),
        ),
        sa.CheckConstraint(
            "total_grades >= 0",
            name=op.f("ck_grade_distributions_total_grades_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_grade_distributions_course_id_courses"),
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            name=op.f("fk_grade_distributions_term_id_terms"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grade_distributions")),
        sa.UniqueConstraint(
            "term_id", "crn", "source", name="uq_grade_distributions_term_crn_source"
        ),
    )


def downgrade() -> None:
    op.drop_table("grade_distributions")
    op.drop_table("course_attributes")
    op.drop_table("ingest_runs")
    op.drop_table("courses")
    op.drop_table("terms")
