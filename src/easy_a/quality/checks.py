from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from easy_a.analytics.confidence import ConfidenceLabel
from easy_a.analytics.queries import get_current_section_historical_analytics
from easy_a.common.instructors import CurrentInstructorStatus, get_current_instructor_state
from easy_a.common.terms import normalize_banner_term_code
from easy_a.models import (
    Course,
    GradeDistribution,
    SeatSnapshot,
    Section,
    SectionInstructor,
    Term,
)
from easy_a.quality.models import FindingSeverity, QualityFinding, QualityReport
from easy_a.schedule.normalize import DELIVERY_METHOD_LABELS

DEFAULT_STALE_AFTER_DAYS = 7


@dataclass(frozen=True)
class SectionIdentity:
    term: str
    crn: str
    section_id: int | None = None


@dataclass(frozen=True)
class SeatValues:
    capacity: int | None
    enrollment: int | None
    seats_remaining: int | None
    wait_seats_available: int | None


def run_quality_checks(
    session: Session,
    term_code: str | int,
    *,
    stale_after: timedelta = timedelta(days=DEFAULT_STALE_AFTER_DAYS),
    as_of: datetime | None = None,
) -> QualityReport:
    if stale_after.total_seconds() < 0:
        raise ValueError("Stale observation threshold must be non-negative.")

    term = normalize_banner_term_code(term_code)
    generated_at = _as_utc(as_of or datetime.now(UTC))
    term_row = session.scalar(select(Term).where(Term.banner_code == term))
    if term_row is None:
        return QualityReport.from_findings(
            term=term,
            generated_at=generated_at,
            section_count=0,
            findings=[
                QualityFinding(
                    check_id="missing_term",
                    severity=FindingSeverity.error,
                    term=term,
                    message="The requested term is not present in the database.",
                )
            ],
        )

    section_course_rows = session.execute(
        select(Section, Course)
        .join(Course, Section.course_id == Course.id)
        .where(Section.term_id == term_row.id)
        .order_by(Section.crn, Section.id)
    ).all()
    section_course_pairs = [(row[0], row[1]) for row in section_course_rows]
    sections = [section for section, _course in section_course_pairs]
    findings = check_duplicate_section_identities(
        [
            SectionIdentity(term=term, crn=section.crn, section_id=section.id)
            for section in sections
        ]
    )
    findings.extend(_check_grades(session, term_row))
    findings.extend(_check_orphan_instructor_observations(session))
    findings.extend(_check_seats(session, term_row, sections))
    findings.extend(_check_delivery_methods(term, sections))
    findings.extend(_check_instructor_state(session, term, sections))
    findings.extend(
        _check_stale_schedule_observations(
            term,
            sections,
            as_of=generated_at,
            stale_after=stale_after,
        )
    )
    findings.extend(_check_analytics(session, term, section_course_pairs))
    return QualityReport.from_findings(
        term=term,
        generated_at=generated_at,
        section_count=len(sections),
        findings=findings,
    )


def check_duplicate_section_identities(
    identities: Sequence[SectionIdentity],
) -> list[QualityFinding]:
    counts = Counter((identity.term, identity.crn) for identity in identities)
    return [
        QualityFinding(
            check_id="duplicate_section_identity",
            severity=FindingSeverity.error,
            term=term,
            crn=crn,
            message=f"Found {count} section records with the same term and CRN.",
        )
        for (term, crn), count in sorted(counts.items())
        if count > 1
    ]


def check_seat_values(
    values: SeatValues,
    *,
    term: str,
    crn: str,
    source_record: str,
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    for label, value in (
        ("capacity", values.capacity),
        ("enrollment", values.enrollment),
        ("wait_seats_available", values.wait_seats_available),
    ):
        if value is not None and value < 0:
            findings.append(
                QualityFinding(
                    check_id="impossible_seat_value",
                    severity=FindingSeverity.error,
                    term=term,
                    crn=crn,
                    source_record=source_record,
                    message=f"{label} cannot be negative (observed {value}).",
                )
            )

    capacity = values.capacity
    enrollment = values.enrollment
    remaining = values.seats_remaining
    if (
        capacity is not None
        and enrollment is not None
        and remaining is not None
        and capacity >= 0
        and enrollment >= 0
    ):
        expected_remaining = capacity - enrollment
        if remaining != expected_remaining:
            findings.append(
                QualityFinding(
                    check_id="inconsistent_seat_count",
                    severity=FindingSeverity.error,
                    term=term,
                    crn=crn,
                    source_record=source_record,
                    message=(
                        "seats_remaining is inconsistent with capacity and enrollment "
                        f"(expected {expected_remaining}, observed {remaining})."
                    ),
                )
            )
    return findings


def _check_grades(session: Session, term: Term) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    distributions = session.scalars(
        select(GradeDistribution)
        .where(GradeDistribution.term_id == term.id)
        .order_by(GradeDistribution.crn, GradeDistribution.id)
    ).all()
    for distribution in distributions:
        count_sum = (
            distribution.a_count
            + distribution.b_count
            + distribution.c_count
            + distribution.d_count
            + distribution.f_count
            + distribution.i_count
            + distribution.s_count
            + distribution.u_count
            + distribution.w_count
            + distribution.other_count
        )
        if count_sum != distribution.total_grades:
            findings.append(
                QualityFinding(
                    check_id="grade_total_mismatch",
                    severity=FindingSeverity.error,
                    term=term.banner_code,
                    crn=distribution.crn,
                    source_record=f"grade_distribution:{distribution.id}",
                    message=(
                        f"Grade bucket sum {count_sum} does not equal "
                        f"Total Grades {distribution.total_grades}."
                    ),
                )
            )

    orphan_rows = session.execute(
        select(GradeDistribution.id, GradeDistribution.crn)
        .outerjoin(
            Section,
            and_(
                Section.term_id == GradeDistribution.term_id,
                Section.crn == GradeDistribution.crn,
            ),
        )
        .where(GradeDistribution.term_id == term.id, Section.id.is_(None))
        .order_by(GradeDistribution.crn, GradeDistribution.id)
    ).all()
    findings.extend(
        QualityFinding(
            check_id="orphan_grade_row",
            severity=FindingSeverity.error,
            term=term.banner_code,
            crn=crn,
            source_record=f"grade_distribution:{distribution_id}",
            message="Grade distribution has no matching section for this term and CRN.",
        )
        for distribution_id, crn in orphan_rows
    )
    return findings


def _check_orphan_instructor_observations(session: Session) -> list[QualityFinding]:
    rows = session.execute(
        select(SectionInstructor.id, SectionInstructor.section_id)
        .outerjoin(Section, Section.id == SectionInstructor.section_id)
        .where(Section.id.is_(None))
        .order_by(SectionInstructor.id)
    ).all()
    return [
        QualityFinding(
            check_id="orphan_instructor_observation",
            severity=FindingSeverity.error,
            source_record=f"section_instructor:{observation_id}",
            message=f"Instructor observation references missing section {section_id}.",
        )
        for observation_id, section_id in rows
    ]


def _check_seats(
    session: Session,
    term: Term,
    sections: Sequence[Section],
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    snapshots = session.execute(
        select(SeatSnapshot, Section.crn)
        .join(Section, SeatSnapshot.section_id == Section.id)
        .where(Section.term_id == term.id)
        .order_by(Section.crn, SeatSnapshot.observed_at, SeatSnapshot.id)
    ).all()
    section_ids_with_snapshots = {snapshot.section_id for snapshot, _ in snapshots}
    for snapshot, crn in snapshots:
        findings.extend(
            check_seat_values(
                SeatValues(
                    capacity=snapshot.capacity,
                    enrollment=snapshot.enrollment,
                    seats_remaining=snapshot.seats_remaining,
                    wait_seats_available=snapshot.wait_seats_available,
                ),
                term=term.banner_code,
                crn=crn,
                source_record=f"seat_snapshot:{snapshot.id}",
            )
        )

    for section in sections:
        if section.id in section_ids_with_snapshots:
            continue
        findings.extend(
            check_seat_values(
                SeatValues(
                    capacity=section.capacity,
                    enrollment=section.enrollment,
                    seats_remaining=section.seats_remaining,
                    wait_seats_available=section.wait_seats_available,
                ),
                term=term.banner_code,
                crn=section.crn,
                source_record=f"section:{section.id}",
            )
        )
    return findings


def _check_delivery_methods(
    term: str,
    sections: Sequence[Section],
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    for section in sections:
        if section.delivery_method is None:
            continue
        code = section.delivery_method.strip().upper()
        if code not in DELIVERY_METHOD_LABELS:
            findings.append(
                QualityFinding(
                    check_id="unknown_delivery_method",
                    severity=FindingSeverity.warning,
                    term=term,
                    crn=section.crn,
                    source_record=f"section:{section.id}",
                    message=f"Unknown delivery-method code {code!r}.",
                )
            )
    return findings


def _check_instructor_state(
    session: Session,
    term: str,
    sections: Sequence[Section],
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    for section in sections:
        state = get_current_instructor_state(session, section.id)
        if state.status is CurrentInstructorStatus.ambiguous_latest_state:
            findings.append(
                QualityFinding(
                    check_id="ambiguous_instructor",
                    severity=FindingSeverity.warning,
                    term=term,
                    crn=section.crn,
                    source_record=f"section:{section.id}",
                    message=(
                        "Latest instructor observation contains multiple names: "
                        + " / ".join(state.latest_names)
                    ),
                )
            )
    return findings


def _check_stale_schedule_observations(
    term: str,
    sections: Sequence[Section],
    *,
    as_of: datetime,
    stale_after: timedelta,
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    cutoff = as_of - stale_after
    for section in sections:
        observed_at = _as_utc(section.last_seen_at)
        if observed_at < cutoff:
            age_days = (as_of - observed_at).total_seconds() / 86400
            findings.append(
                QualityFinding(
                    check_id="stale_schedule_observation",
                    severity=FindingSeverity.warning,
                    term=term,
                    crn=section.crn,
                    source_record=f"section:{section.id}",
                    message=(
                        f"Latest schedule observation is {age_days:.1f} days old; "
                        "stale does not imply invalid."
                    ),
                )
            )
    return findings


def _check_analytics(
    session: Session,
    term: str,
    section_course_rows: Sequence[tuple[Section, Course]],
) -> list[QualityFinding]:
    analytics_by_crn = {}
    course_keys = sorted(
        {(course.subject, course.number) for _, course in section_course_rows}
    )
    for subject, course_number in course_keys:
        for row in get_current_section_historical_analytics(
            session,
            term_code=term,
            subject=subject,
            course_number=course_number,
        ):
            analytics_by_crn[row.crn] = row.stats

    findings: list[QualityFinding] = []
    for section, _course in section_course_rows:
        stats = analytics_by_crn.get(section.crn)
        if stats is None or stats.section_count == 0 or stats.total_grade_count == 0:
            findings.append(
                QualityFinding(
                    check_id="no_historical_analytics",
                    severity=FindingSeverity.info,
                    term=term,
                    crn=section.crn,
                    source_record=f"section:{section.id}",
                    message="Section has no historical grade analytics coverage.",
                )
            )
        if stats is None or stats.confidence_label is ConfidenceLabel.low:
            findings.append(
                QualityFinding(
                    check_id="low_confidence_ranking",
                    severity=FindingSeverity.warning,
                    term=term,
                    crn=section.crn,
                    source_record=f"section:{section.id}",
                    message="Computed historical ranking confidence is low.",
                )
            )
    return findings


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
