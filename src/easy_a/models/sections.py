from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from easy_a.db import Base


class Section(Base):
    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("term_id", "crn", name="uq_sections_term_crn"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id"), nullable=False)
    crn: Mapped[str] = mapped_column(String(16), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    section_number: Mapped[str] = mapped_column(String(32), nullable=False)
    campus: Mapped[str] = mapped_column(String(128), nullable=False)
    session: Mapped[str] = mapped_column(String(128), nullable=False)
    section_type: Mapped[str] = mapped_column(String(128), nullable=False)
    credits: Mapped[str | None] = mapped_column(String(32), nullable=True)
    primary_status: Mapped[str] = mapped_column(String(32), nullable=False)
    secondary_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    delivery_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    days: Mapped[str | None] = mapped_column(String(32), nullable=True)
    start_time: Mapped[time | None] = mapped_column(Time(), nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time(), nullable=True)
    building: Mapped[str | None] = mapped_column(String(64), nullable=True)
    room: Mapped[str | None] = mapped_column(String(64), nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enrollment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seats_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wait_seats_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    fees_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    instructors: Mapped[list[SectionInstructor]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
    )
    seat_snapshots: Mapped[list[SeatSnapshot]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
    )
    syllabi: Mapped[list[Syllabus]] = relationship(back_populates="section")


class SectionInstructor(Base):
    __tablename__ = "section_instructors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
    )
    name_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    name_normalized: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    section: Mapped[Section] = relationship(back_populates="instructors")


class SeatSnapshot(Base):
    __tablename__ = "seat_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enrollment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seats_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wait_seats_available: Mapped[int | None] = mapped_column(Integer, nullable=True)

    section: Mapped[Section] = relationship(back_populates="seat_snapshots")


class Syllabus(Base):
    __tablename__ = "syllabi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("sections.id"), nullable=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id"), nullable=False)
    crn: Mapped[str] = mapped_column(String(16), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    section_number: Mapped[str] = mapped_column(String(32), nullable=False)
    instructor_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    view_url: Mapped[str] = mapped_column(Text, nullable=False)
    print_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    content_html: Mapped[str] = mapped_column(Text, nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    section: Mapped[Section | None] = relationship(back_populates="syllabi")
