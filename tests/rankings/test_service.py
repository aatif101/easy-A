from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlalchemy.orm import Session

from easy_a.analytics.confidence import ScoreSource
from easy_a.analytics.queries import (
    SectionHistoricalAnalytics,
    get_current_section_historical_analytics,
)
from easy_a.grades.ingest import ingest_grade_file
from easy_a.models import (
    CourseAttribute,
    GradeDistribution,
    SeatSnapshot,
    Section,
    SectionInstructor,
    Syllabus,
)
from easy_a.rankings import RankingFreshness, rank_course_sections, rank_section
from easy_a.schedule.ingest import ingest_schedule_html

NOW = datetime(2026, 9, 1, tzinfo=UTC)
FIXTURES = Path(__file__).parents[1] / "fixtures"
GRADE_HEADER = [
    "course",
    "A",
    "% A",
    "B",
    "% B",
    "C",
    "% C",
    "D",
    "% D",
    "F",
    "% F",
    "I",
    "% I",
    "S",
    "% S",
    "U",
    "% U",
    "W",
    "% W",
    "O",
    "% O",
    "Total Grades",
]


def test_staff_current_section_falls_back_to_course_analytics(db_session: Session) -> None:
    _add_grade(db_session, term_id=2, crn="89033", a=40, b=20, w=5)
    _add_section(
        db_session,
        term_id=1,
        crn="12345",
        instructor="Staff",
        delivery_method="HB",
        capacity=30,
        enrollment=23,
        seats_remaining=7,
    )
    db_session.commit()

    ranking = rank_section(db_session, term="202701", crn="12345")

    assert ranking.instructor == "Staff"
    assert ranking.score_source is ScoreSource.course
    assert ranking.historical_analytics.score_source is ScoreSource.course
    assert ranking.modality.delivery_method == "HB"
    assert ranking.modality.provenance.freshness is RankingFreshness.current
    assert ranking.seats_remaining == 7
    assert ranking.seats.provenance.source == "sections.current_seat_fields"


def test_staff_old_named_instructor_latest_is_displayed_and_scored(
    db_session: Session,
) -> None:
    _add_section(db_session, term_id=2, crn="89033", instructor="I. Rothstein")
    _add_grade(db_session, term_id=2, crn="89033", a=80, b=20, w=5)
    current = _add_section(db_session, term_id=1, crn="71001", instructor="Staff")
    _observe_instructor(
        db_session,
        section_id=current.id,
        name="I. Rothstein",
        observed_at=NOW + timedelta(days=1),
    )
    db_session.commit()

    ranking = rank_section(db_session, term="202701", crn="71001")
    analytics_row = _analytics_row_for(db_session, crn="71001")

    assert ranking.instructor == "I. Rothstein"
    assert analytics_row.instructor == "I. Rothstein"
    assert ranking.score_source is ScoreSource.instructor_course
    assert analytics_row.stats.score_source is ScoreSource.instructor_course


def test_old_instructor_a_latest_instructor_b_is_displayed_and_scored(
    db_session: Session,
) -> None:
    _add_section(db_session, term_id=2, crn="89033", instructor="Instructor B")
    _add_grade(db_session, term_id=2, crn="89033", a=80, b=20, w=5)
    current = _add_section(db_session, term_id=1, crn="71002", instructor="Instructor A")
    _observe_instructor(
        db_session,
        section_id=current.id,
        name="Instructor B",
        observed_at=NOW + timedelta(days=1),
    )
    db_session.commit()

    ranking = rank_section(db_session, term="202701", crn="71002")
    analytics_row = _analytics_row_for(db_session, crn="71002")

    assert ranking.instructor == "Instructor B"
    assert analytics_row.instructor == "Instructor B"
    assert ranking.score_source is ScoreSource.instructor_course
    assert analytics_row.stats.score_source is ScoreSource.instructor_course


def test_ambiguous_latest_instructor_state_is_unresolved_and_course_scored(
    db_session: Session,
) -> None:
    _add_section(db_session, term_id=2, crn="89033", instructor="Instructor B")
    _add_grade(db_session, term_id=2, crn="89033", a=80, b=20, w=5)
    current = _add_section(db_session, term_id=1, crn="71003", instructor="Instructor A")
    latest_at = NOW + timedelta(days=1)
    _observe_instructor(
        db_session,
        section_id=current.id,
        name="Instructor B",
        observed_at=latest_at,
    )
    _observe_instructor(
        db_session,
        section_id=current.id,
        name="Instructor C",
        observed_at=latest_at,
    )
    db_session.commit()

    ranking = rank_section(db_session, term="202701", crn="71003")
    analytics_row = _analytics_row_for(db_session, crn="71003")

    assert ranking.instructor is None
    assert analytics_row.instructor is None
    assert ranking.instructor_provenance.detail == (
        "ambiguous latest instructor state: Instructor B / Instructor C"
    )
    assert ranking.score_source is ScoreSource.course
    assert analytics_row.stats.score_source is ScoreSource.course


def test_latest_staff_is_displayed_but_uses_course_analytics(db_session: Session) -> None:
    _add_section(db_session, term_id=2, crn="89033", instructor="I. Rothstein")
    _add_grade(db_session, term_id=2, crn="89033", a=80, b=20, w=5)
    current = _add_section(db_session, term_id=1, crn="71004", instructor="I. Rothstein")
    _observe_instructor(
        db_session,
        section_id=current.id,
        name="Staff",
        observed_at=NOW + timedelta(days=1),
    )
    db_session.commit()

    ranking = rank_section(db_session, term="202701", crn="71004")
    analytics_row = _analytics_row_for(db_session, crn="71004")

    assert ranking.instructor == "Staff"
    assert analytics_row.instructor == "Staff"
    assert ranking.score_source is ScoreSource.course
    assert analytics_row.stats.score_source is ScoreSource.course


def test_ranking_displayed_instructor_matches_analytics_resolved_instructor(
    db_session: Session,
) -> None:
    _add_grade(db_session, term_id=2, crn="89033", a=30, b=10, w=4)
    _add_section(db_session, term_id=1, crn="71005", instructor="Staff")
    db_session.commit()

    ranking = rank_section(db_session, term="202701", crn="71005")
    analytics_row = _analytics_row_for(db_session, crn="71005")

    assert ranking.instructor == analytics_row.instructor


def test_named_instructor_with_sufficient_history_uses_instructor_course(
    db_session: Session,
) -> None:
    _add_section(db_session, term_id=2, crn="89033", instructor="I. Rothstein")
    _add_grade(db_session, term_id=2, crn="89033", a=80, b=20, w=5)
    current = _add_section(
        db_session,
        term_id=1,
        crn="70001",
        instructor="I. Rothstein",
        capacity=35,
        enrollment=30,
        seats_remaining=5,
    )
    db_session.add(
        SeatSnapshot(
            section_id=current.id,
            observed_at=NOW + timedelta(days=1),
            capacity=40,
            enrollment=37,
            seats_remaining=3,
            wait_seats_available=0,
        )
    )
    db_session.commit()

    ranking = rank_section(db_session, term="202701", crn="70001")

    assert ranking.score_source is ScoreSource.instructor_course
    assert ranking.historical_analytics.mapped_instructor_section_count == 1
    assert ranking.seats_remaining == 3
    assert ranking.seats.provenance.source == "seat_snapshots"


def test_gened_attributes_and_current_section_note_signals_are_included(
    db_session: Session,
) -> None:
    _add_grade(db_session, term_id=2, crn="89033", a=30, b=10, w=4)
    db_session.add(
        CourseAttribute(
            course_id=10,
            attribute_code="SMEL",
            attribute_label="Enhanced General Education Mathematics",
        )
    )
    _add_section(
        db_session,
        term_id=1,
        crn="70002",
        instructor="Staff",
        note="Quizzes and exams are in person in the SMART Lab.",
    )
    db_session.commit()

    ranking = rank_section(db_session, term="202701", crn="70002")

    assert [(attribute.code, attribute.label) for attribute in ranking.gened_attributes] == [
        ("SMEL", "Enhanced General Education Mathematics")
    ]
    assert ranking.gened_provenance.freshness is RankingFreshness.current
    assert ranking.signal_provenance.freshness is RankingFreshness.current
    assert ranking.signal_provenance.source == "schedule_section_note"
    assert {signal.signal_type for signal in ranking.signals} >= {"exam_location", "quiz"}
    assert all(signal.freshness is RankingFreshness.current for signal in ranking.signals)


def test_historical_syllabus_signals_are_marked_historical(db_session: Session) -> None:
    _add_grade(db_session, term_id=2, crn="89033", a=80, b=20, w=5)
    _add_section(db_session, term_id=2, crn="89033", instructor="I. Rothstein")
    _add_section(db_session, term_id=1, crn="70003", instructor="I. Rothstein")
    _add_syllabus(
        db_session,
        document_id="historical-rothstein",
        term_id=2,
        crn="89033",
        instructor="I. Rothstein",
        text="Late work is not accepted.",
    )
    db_session.commit()

    ranking = rank_section(db_session, term="202701", crn="70003")

    assert ranking.signal_provenance.freshness is RankingFreshness.historical
    assert ranking.signal_provenance.source == "historical_same_instructor_course"
    assert ranking.signals[0].freshness is RankingFreshness.historical
    assert ranking.signals[0].source_term == "202408"
    assert ranking.signals[0].evidence == "Late work is not accepted."


def test_unavailable_signals_remain_unavailable(db_session: Session) -> None:
    _add_grade(db_session, term_id=2, crn="89033", a=30, b=10, w=4)
    _add_section(db_session, term_id=1, crn="70004", instructor="Staff")
    db_session.commit()

    ranking = rank_section(db_session, term="202701", crn="70004")

    assert ranking.signals == ()
    assert ranking.signal_provenance.freshness is RankingFreshness.unavailable
    assert ranking.signal_provenance.source == "unavailable"


def test_seat_modality_and_signal_changes_do_not_change_easiness_score(
    db_session: Session,
) -> None:
    section = _add_section(
        db_session,
        term_id=1,
        crn="70005",
        instructor="Staff",
        delivery_method="CL",
        seats_remaining=0,
    )
    _add_grade(db_session, term_id=2, crn="89033", a=30, b=10, w=4)
    db_session.commit()

    before = rank_section(db_session, term="202701", crn="70005")

    section.delivery_method = "AD"
    section.seats_remaining = 99
    section.section_note = "Attendance is required."
    db_session.add(
        SeatSnapshot(
            section_id=section.id,
            observed_at=NOW + timedelta(days=1),
            capacity=120,
            enrollment=20,
            seats_remaining=100,
            wait_seats_available=5,
        )
    )
    db_session.commit()

    after = rank_section(db_session, term="202701", crn="70005")

    assert after.easiness_score == pytest.approx(before.easiness_score)
    assert after.smoothed_withdrawal_rate == pytest.approx(before.smoothed_withdrawal_rate)
    assert after.modality.delivery_method == "AD"
    assert after.seats_remaining == 100
    assert after.signal_provenance.source == "schedule_section_note"


def test_same_crn_in_different_terms_stays_distinct(db_session: Session) -> None:
    _add_grade(db_session, term_id=2, crn="89033", a=20)
    _add_section(
        db_session,
        term_id=1,
        crn="55555",
        instructor="Staff",
        seats_remaining=1,
    )
    _add_section(
        db_session,
        term_id=3,
        crn="55555",
        instructor="Different Instructor",
        seats_remaining=9,
    )
    db_session.commit()

    spring = rank_section(db_session, term="202701", crn="55555")
    summer = rank_section(db_session, term="202605", crn="55555")

    assert spring.term == "202701"
    assert spring.instructor == "Staff"
    assert spring.seats_remaining == 1
    assert summer.term == "202605"
    assert summer.instructor == "Different Instructor"
    assert summer.seats_remaining == 9


def test_safe_rothstein_202408_89033_fixture_still_joins_for_ranking(
    tmp_path: Path,
    db_session: Session,
) -> None:
    workbook_path = tmp_path / "fall_2024_89033.xlsx"
    _write_grade_workbook(workbook_path)
    schedule_html = (FIXTURES / "schedule_historical_202408_89033.html").read_text(
        encoding="utf-8"
    )

    ingest_grade_file(db_session, "202408", workbook_path)
    ingest_schedule_html(db_session, schedule_html, "202408", observed_at=NOW)
    _add_section(db_session, term_id=1, crn="70006", instructor="Staff")
    db_session.commit()

    ranking = rank_section(db_session, term="202701", crn="70006")

    assert ranking.score_source is ScoreSource.course
    assert ranking.historical_analytics.total_grade_count == 15
    assert ranking.historical_analytics.section_count == 1
    assert ranking.historical_analytics.mapped_instructor_section_count == 1
    assert ranking.historical_analytics.provenance.freshness is RankingFreshness.historical


def test_course_level_rankings_return_all_sections_in_crn_order(db_session: Session) -> None:
    _add_grade(db_session, term_id=2, crn="89033", a=20)
    _add_section(db_session, term_id=1, crn="70008", instructor="Staff")
    _add_section(db_session, term_id=1, crn="70007", instructor="Staff")
    db_session.commit()

    rankings = rank_course_sections(
        db_session,
        term="202701",
        subject="MAC",
        course_number="1105",
    )

    assert [ranking.crn for ranking in rankings] == ["70007", "70008"]


def _add_grade(
    session: Session,
    *,
    term_id: int,
    crn: str,
    course_id: int = 10,
    a: int = 0,
    b: int = 0,
    c: int = 0,
    d: int = 0,
    f: int = 0,
    w: int = 0,
) -> GradeDistribution:
    completed = a + b + c + d + f
    distribution = GradeDistribution(
        term_id=term_id,
        crn=crn,
        course_id=course_id,
        section_number_raw="001",
        section_suffix_raw="C",
        campus_raw="Tampa",
        a_count=a,
        b_count=b,
        c_count=c,
        d_count=d,
        f_count=f,
        i_count=0,
        s_count=0,
        u_count=0,
        w_count=w,
        other_count=0,
        total_grades=completed + w,
        source=f"synthetic-{term_id}-{crn}-{a}-{b}-{c}-{d}-{f}-{w}",
        source_hash="synthetic",
    )
    session.add(distribution)
    session.flush()
    return distribution


def _add_section(
    session: Session,
    *,
    term_id: int,
    crn: str,
    instructor: str,
    course_id: int = 10,
    delivery_method: str | None = "CL",
    capacity: int | None = None,
    enrollment: int | None = None,
    seats_remaining: int | None = None,
    note: str | None = None,
) -> Section:
    section = Section(
        term_id=term_id,
        crn=crn,
        course_id=course_id,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Active",
        secondary_status=None,
        delivery_method=delivery_method,
        capacity=capacity,
        enrollment=enrollment,
        seats_remaining=seats_remaining,
        wait_seats_available=0 if seats_remaining is not None else None,
        section_note=note,
        first_seen_at=NOW,
        last_seen_at=NOW,
    )
    session.add(section)
    session.flush()
    session.add(
        SectionInstructor(
            section_id=section.id,
            name_raw=instructor,
            name_normalized=instructor.lower(),
            source="synthetic",
            observed_at=NOW,
        )
    )
    session.flush()
    return section


def _add_syllabus(
    session: Session,
    *,
    document_id: str,
    term_id: int,
    crn: str,
    instructor: str,
    text: str,
    course_id: int = 10,
) -> Syllabus:
    syllabus = Syllabus(
        document_id=document_id,
        term_id=term_id,
        crn=crn,
        course_id=course_id,
        section_number="001",
        instructor_raw=instructor,
        organization="Synthetic",
        title="Synthetic syllabus",
        view_url=f"https://example.test/{document_id}",
        fetched_at=NOW,
        content_html=f"<p>{text}</p>",
        content_text=text,
        content_hash=document_id.ljust(64, "0")[:64],
    )
    session.add(syllabus)
    session.flush()
    return syllabus


def _observe_instructor(
    session: Session,
    *,
    section_id: int,
    name: str,
    observed_at: datetime,
) -> None:
    session.add(
        SectionInstructor(
            section_id=section_id,
            name_raw=name,
            name_normalized=name.lower(),
            source="synthetic",
            observed_at=observed_at,
        )
    )
    session.flush()


def _analytics_row_for(db_session: Session, *, crn: str) -> SectionHistoricalAnalytics:
    rows = get_current_section_historical_analytics(
        db_session,
        term_code="202701",
        subject="MAC",
        course_number="1105",
    )
    return next(row for row in rows if row.crn == crn)


def _write_grade_workbook(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    assert worksheet is not None
    worksheet.append(GRADE_HEADER)
    worksheet.append(
        [
            "MAC-1105 -001-C (89033)",
            10,
            None,
            4,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            1,
            None,
            0,
            None,
            15,
        ]
    )
    workbook.save(path)
