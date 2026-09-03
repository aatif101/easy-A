from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from easy_a.models import GradeDistribution, Section, SectionInstructor
from easy_a.quality import (
    QualityFinding,
    SeatValues,
    SectionIdentity,
    check_duplicate_section_identities,
    check_seat_values,
    run_quality_checks,
)

NOW = datetime(2026, 9, 3, 12, tzinfo=UTC)


def test_duplicate_term_crn_is_an_error() -> None:
    findings = check_duplicate_section_identities(
        [
            SectionIdentity(term="202701", crn="12345", section_id=1),
            SectionIdentity(term="202701", crn="12345", section_id=2),
            SectionIdentity(term="202408", crn="12345", section_id=3),
        ]
    )

    assert len(findings) == 1
    assert findings[0].check_id == "duplicate_section_identity"
    assert findings[0].severity == "error"
    assert findings[0].term == "202701"
    assert findings[0].crn == "12345"


def test_grade_total_mismatch_is_an_error(db_session: Session) -> None:
    section = _section(crn="12345")
    db_session.add(section)
    db_session.flush()
    db_session.add(_grade(crn="12345", total_grades=99))

    report = run_quality_checks(db_session, "202701", as_of=NOW)

    finding = _finding(report.findings, "grade_total_mismatch")
    assert finding.severity == "error"
    assert finding.crn == "12345"


def test_orphan_grade_row_is_an_error(db_session: Session) -> None:
    db_session.add(_grade(crn="99999", total_grades=10))

    report = run_quality_checks(db_session, "202701", as_of=NOW)

    finding = _finding(report.findings, "orphan_grade_row")
    assert finding.severity == "error"
    assert finding.crn == "99999"


def test_orphan_instructor_observation_is_an_error(db_session: Session) -> None:
    db_session.add(
        SectionInstructor(
            section_id=999,
            name_raw="Orphan Instructor",
            name_normalized="orphan instructor",
            source="synthetic",
            observed_at=NOW,
        )
    )

    report = run_quality_checks(db_session, "202701", as_of=NOW)

    finding = _finding(report.findings, "orphan_instructor_observation")
    assert finding.severity == "error"
    assert "missing section 999" in finding.message


def test_impossible_and_inconsistent_seat_values_are_errors() -> None:
    impossible = check_seat_values(
        SeatValues(capacity=-1, enrollment=0, seats_remaining=0, wait_seats_available=-2),
        term="202701",
        crn="12345",
        source_record="seat_snapshot:1",
    )
    inconsistent = check_seat_values(
        SeatValues(capacity=30, enrollment=20, seats_remaining=5, wait_seats_available=0),
        term="202701",
        crn="12346",
        source_record="seat_snapshot:2",
    )

    assert [finding.check_id for finding in impossible] == [
        "impossible_seat_value",
        "impossible_seat_value",
    ]
    assert [finding.check_id for finding in inconsistent] == ["inconsistent_seat_count"]
    assert all(finding.severity == "error" for finding in impossible + inconsistent)


def test_unknown_delivery_method_is_a_warning(db_session: Session) -> None:
    db_session.add(_section(crn="12345", delivery_method="XX"))

    report = run_quality_checks(db_session, "202701", as_of=NOW)

    finding = _finding(report.findings, "unknown_delivery_method")
    assert finding.severity == "warning"
    assert "XX" in finding.message


def test_ambiguous_latest_instructor_is_a_warning(db_session: Session) -> None:
    section = _section(crn="12345")
    db_session.add(section)
    db_session.flush()
    db_session.add_all(
        [
            _instructor(section.id, "Instructor A"),
            _instructor(section.id, "Instructor B"),
        ]
    )

    report = run_quality_checks(db_session, "202701", as_of=NOW)

    finding = _finding(report.findings, "ambiguous_instructor")
    assert finding.severity == "warning"
    assert "Instructor A / Instructor B" in finding.message


def test_stale_schedule_observation_is_a_warning_not_invalid(db_session: Session) -> None:
    db_session.add(_section(crn="12345", observed_at=NOW - timedelta(days=8)))

    report = run_quality_checks(
        db_session,
        "202701",
        stale_after=timedelta(days=7),
        as_of=NOW,
    )

    finding = _finding(report.findings, "stale_schedule_observation")
    assert finding.severity == "warning"
    assert "does not imply invalid" in finding.message


def test_no_analytics_and_low_confidence_are_reported(db_session: Session) -> None:
    db_session.add(_section(crn="12345"))

    report = run_quality_checks(db_session, "202701", as_of=NOW)

    no_coverage = _finding(report.findings, "no_historical_analytics")
    low_confidence = _finding(report.findings, "low_confidence_ranking")
    assert no_coverage.severity == "info"
    assert low_confidence.severity == "warning"


def _section(
    *,
    crn: str,
    delivery_method: str | None = "CL",
    observed_at: datetime = NOW,
) -> Section:
    return Section(
        term_id=1,
        crn=crn,
        course_id=10,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Open",
        delivery_method=delivery_method,
        first_seen_at=observed_at,
        last_seen_at=observed_at,
    )


def _grade(*, crn: str, total_grades: int) -> GradeDistribution:
    return GradeDistribution(
        term_id=1,
        crn=crn,
        course_id=10,
        section_number_raw="001",
        a_count=10,
        b_count=0,
        c_count=0,
        d_count=0,
        f_count=0,
        i_count=0,
        s_count=0,
        u_count=0,
        w_count=0,
        other_count=0,
        total_grades=total_grades,
        source=f"synthetic-{crn}",
        source_hash="synthetic",
    )


def _instructor(section_id: int, name: str) -> SectionInstructor:
    return SectionInstructor(
        section_id=section_id,
        name_raw=name,
        name_normalized=name.lower(),
        source="synthetic",
        observed_at=NOW,
    )


def _finding(findings: tuple[QualityFinding, ...], check_id: str) -> QualityFinding:
    return next(finding for finding in findings if finding.check_id == check_id)
