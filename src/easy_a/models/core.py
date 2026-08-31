from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from easy_a.db import Base


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Term(Timestamped, Base):
    __tablename__ = "terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    banner_code: Mapped[str] = mapped_column(String(6), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    grade_distributions: Mapped[list[GradeDistribution]] = relationship(back_populates="term")


class Course(Timestamped, Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("subject", "number", "catalog_edition", name="uq_courses_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject: Mapped[str] = mapped_column(String(16), nullable=False)
    number: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    credits: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prerequisites: Mapped[str | None] = mapped_column(Text, nullable=True)
    other_information: Mapped[str | None] = mapped_column(Text, nullable=True)
    catalog_edition: Mapped[str] = mapped_column(String(32), nullable=False)

    attributes: Mapped[list[CourseAttribute]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="CourseAttribute.id",
    )
    grade_distributions: Mapped[list[GradeDistribution]] = relationship(back_populates="course")


class CourseAttribute(Base):
    __tablename__ = "course_attributes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    attribute_code: Mapped[str] = mapped_column(String(32), nullable=False)
    attribute_label: Mapped[str] = mapped_column(String(255), nullable=False)

    course: Mapped[Course] = relationship(back_populates="attributes")


class GradeDistribution(Base):
    __tablename__ = "grade_distributions"
    __table_args__ = (
        UniqueConstraint("term_id", "crn", "source", name="uq_grade_distributions_term_crn_source"),
        CheckConstraint("a_count >= 0", name="a_count_nonnegative"),
        CheckConstraint("b_count >= 0", name="b_count_nonnegative"),
        CheckConstraint("c_count >= 0", name="c_count_nonnegative"),
        CheckConstraint("d_count >= 0", name="d_count_nonnegative"),
        CheckConstraint("f_count >= 0", name="f_count_nonnegative"),
        CheckConstraint("i_count >= 0", name="i_count_nonnegative"),
        CheckConstraint("s_count >= 0", name="s_count_nonnegative"),
        CheckConstraint("u_count >= 0", name="u_count_nonnegative"),
        CheckConstraint("w_count >= 0", name="w_count_nonnegative"),
        CheckConstraint("other_count >= 0", name="other_count_nonnegative"),
        CheckConstraint("total_grades >= 0", name="total_grades_nonnegative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id"), nullable=False)
    crn: Mapped[str] = mapped_column(String(16), nullable=False)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    section_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_number_raw: Mapped[str] = mapped_column(String(32), nullable=False)
    section_suffix_raw: Mapped[str | None] = mapped_column(String(32), nullable=True)
    campus_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    a_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    b_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    c_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    d_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    f_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    i_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    s_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    u_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    w_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    other_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_grades: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    term: Mapped[Term] = relationship(back_populates="grade_distributions")
    course: Mapped[Course | None] = relationship(back_populates="grade_distributions")


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    records_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
