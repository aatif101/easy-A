from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import scripts.validate_tampa_ingest as v
from easy_a.models import Course, Section
from easy_a.rankings.cache import SectionRankingCache
from easy_a.refresh.targets import CourseTarget, load_targets
from tests.api.test_rankings_search_sql import _historical_analytics, _provenance

NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)
TERM = "202701"
PAIR = ("CHM", "2045", "2045L")


def _add_course(session: Session, subject: str, number: str, course_id: int) -> Course:
    course = Course(
        id=course_id,
        subject=subject,
        number=number,
        title=f"{subject} {number}",
        catalog_edition="2026-2027",
    )
    session.add(course)
    session.flush()
    return course


def _add_section(session: Session, *, course_id: int, crn: str, campus: str = "Tampa") -> Section:
    section = Section(
        term_id=1,
        crn=crn,
        course_id=course_id,
        section_number="001",
        campus=campus,
        session="Full Semester",
        section_type="Lecture",
        primary_status="A",
        first_seen_at=NOW,
        last_seen_at=NOW,
    )
    session.add(section)
    session.flush()
    return section


def _add_ranking(
    session: Session,
    *,
    section: Section,
    course: Course,
    score_source: str,
    effective_n: float,
) -> SectionRankingCache:
    row = SectionRankingCache(
        section_id=section.id,
        term=TERM,
        term_name="Spring 2027",
        subject=course.subject,
        course_number=course.number,
        crn=section.crn,
        course_title=course.title,
        instructor=None,
        easiness_score=0.5,
        smoothed_withdrawal_rate=0.05,
        confidence_label="low",
        score_source=score_source,
        effective_n=effective_n,
        delivery_method=None,
        historical_analytics=_historical_analytics(easiness=0.5, withdrawal=0.05, confidence="low"),
        gened_attributes=[],
        signals=[],
        instructor_provenance=_provenance("unavailable", "section_instructors"),
        gened_provenance=_provenance("unavailable", "course_attributes"),
        signal_provenance=_provenance("unavailable", "schedule/syllabi"),
        section_provenance=_provenance("current", "sections"),
        modality={
            "delivery_method": None,
            "delivery_label": None,
            "provenance": _provenance("current", "sections.delivery_method"),
        },
    )
    session.add(row)
    session.flush()
    return row


def _seed_honest_dataset(session: Session) -> tuple[Course, Course]:
    """A base course (CHM 2045, 2 Tampa sections) and a suffix course (CHM 2045L, 1
    section) with honest rankings: one course-backed row and one honest global fallback."""
    base = _add_course(session, "CHM", "2045", course_id=1001)
    suffix = _add_course(session, "CHM", "2045L", course_id=1002)
    s1 = _add_section(session, course_id=base.id, crn="30001")
    s2 = _add_section(session, course_id=base.id, crn="30002")
    s3 = _add_section(session, course_id=suffix.id, crn="30003")
    _add_ranking(session, section=s1, course=base, score_source="course", effective_n=120.0)
    _add_ranking(session, section=s2, course=base, score_source="global", effective_n=0.0)
    _add_ranking(session, section=s3, course=suffix, score_source="global", effective_n=0.0)
    session.commit()
    return base, suffix


# --- derive_suffix_pairs -----------------------------------------------------------


def test_derive_suffix_pairs_over_real_config_yields_33() -> None:
    config = load_targets(Path("config/course_targets.toml"))
    assert len(v.derive_suffix_pairs(config.targets)) == 33


def test_derive_suffix_pairs_synthetic() -> None:
    targets = (
        CourseTarget(subject="CHM", number="2045"),
        CourseTarget(subject="CHM", number="2045L"),
        CourseTarget(subject="MAC", number="1105"),
    )
    assert v.derive_suffix_pairs(targets) == (("CHM", "2045", "2045L"),)


# --- assert_suffix_exact_ingest ----------------------------------------------------


def test_assert_suffix_exact_ingest_passes_on_honest_dataset(db_session: Session) -> None:
    _seed_honest_dataset(db_session)
    v.assert_suffix_exact_ingest(db_session, TERM, [PAIR])


def test_assert_suffix_exact_ingest_raises_on_leaked_suffix_section(db_session: Session) -> None:
    base, _suffix = _seed_honest_dataset(db_session)
    # Simulate a 2045L section mis-attributed to 2045: reassign the suffix course's
    # only stored section to the base course id.
    leaked = db_session.scalar(select(Section).where(Section.crn == "30003"))
    assert leaked is not None
    leaked.course_id = base.id
    db_session.commit()
    with pytest.raises(AssertionError, match="2045L"):
        v.assert_suffix_exact_ingest(db_session, TERM, [PAIR])


# --- assert_coverage_reconciled -----------------------------------------------------


def test_assert_coverage_reconciled_passes_on_honest_dataset(db_session: Session) -> None:
    _seed_honest_dataset(db_session)
    targets = (
        CourseTarget(subject="CHM", number="2045"),
        CourseTarget(subject="CHM", number="2045L"),
    )
    v.assert_coverage_reconciled(db_session, TERM, targets)


def test_assert_coverage_reconciled_raises_on_untargeted_course(db_session: Session) -> None:
    _seed_honest_dataset(db_session)
    # 2045L is stored but not a configured target -- the 5-vs-10-vs-1402 style discrepancy.
    targets = (CourseTarget(subject="CHM", number="2045"),)
    with pytest.raises(AssertionError, match="2045L"):
        v.assert_coverage_reconciled(db_session, TERM, targets)


# --- assert_honest_coverage ---------------------------------------------------------


def test_assert_honest_coverage_passes_on_honest_dataset(db_session: Session) -> None:
    _seed_honest_dataset(db_session)
    v.assert_honest_coverage(db_session, TERM)


def test_assert_honest_coverage_raises_on_fabricated_course_backed_row(db_session: Session) -> None:
    _seed_honest_dataset(db_session)
    row = db_session.scalar(select(SectionRankingCache).where(SectionRankingCache.crn == "30002"))
    assert row is not None
    # Fabricate: claim course-backed history while effective_n stays 0 (D-20 violation).
    row.score_source = "course"
    db_session.commit()
    with pytest.raises(AssertionError, match="30002"):
        v.assert_honest_coverage(db_session, TERM)
