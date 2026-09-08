from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.models import SeatSnapshot, Section, Term
from easy_a.quality.models import FindingSeverity, QualityFinding
from easy_a.refresh.coverage import coverage_metadata
from easy_a.refresh.targets import CourseTarget
from easy_a.schedule.freshness import SeatFreshness, snapshot_freshness


def coverage_findings(
    session: Session, term: str, targets: tuple[CourseTarget, ...], as_of: datetime
) -> list[QualityFinding]:
    findings = []
    for row in coverage_metadata(session, term, targets):
        for missing, check, message in (
            (not row.catalog_present, "target_missing_catalog", "Target missing from catalog"),
            (row.section_count == 0, "target_missing_sections", "Target has no stored sections"),
        ):
            if missing:
                findings.append(
                    QualityFinding(
                        check_id=check,
                        severity=FindingSeverity.warning,
                        term=term,
                        source_record=f"{row.subject} {row.course_number}",
                        message=message,
                    )
                )
    sections = session.scalars(select(Section).join(Term).where(Term.banner_code == term))
    for section in sections:
        snapshot = session.scalar(
            select(SeatSnapshot)
            .where(SeatSnapshot.section_id == section.id)
            .order_by(SeatSnapshot.observed_at.desc(), SeatSnapshot.id.desc())
            .limit(1)
        )
        if snapshot_freshness(snapshot, as_of=as_of).freshness == SeatFreshness.stale:
            findings.append(
                QualityFinding(
                    check_id="stale_seat_observation",
                    severity=FindingSeverity.warning,
                    term=term,
                    crn=section.crn,
                    message="Latest observed seats exceed the configured stale threshold.",
                )
            )
    return findings
