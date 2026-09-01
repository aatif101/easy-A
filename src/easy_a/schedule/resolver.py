from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from easy_a.schedule.normalize import NormalizedSection, normalize_schedule_row
from easy_a.schedule.parser import parse_schedule_html


class ResolutionOutcome(StrEnum):
    matched = "matched"
    not_found = "not_found"
    ambiguous = "ambiguous"


@dataclass(frozen=True)
class HistoricalResolution:
    outcome: ResolutionOutcome
    section: NormalizedSection | None = None
    candidate_count: int = 0
    reason: str | None = None


def resolve_historical_section(
    html: str,
    *,
    crn: str,
    expected_subject: str | None = None,
    expected_course: str | None = None,
) -> HistoricalResolution:
    normalized_crn = crn.strip()
    if not normalized_crn:
        raise ValueError("CRN cannot be empty.")

    candidates = [
        normalize_schedule_row(row)
        for row in parse_schedule_html(html)
        if row.crn == normalized_crn
    ]
    if not candidates:
        return HistoricalResolution(ResolutionOutcome.not_found)
    if len(candidates) > 1:
        return HistoricalResolution(
            ResolutionOutcome.ambiguous,
            candidate_count=len(candidates),
            reason=f"Found {len(candidates)} rows for CRN {crn}.",
        )

    section = candidates[0]
    if expected_subject is not None and section.subject != expected_subject.strip().upper():
        return HistoricalResolution(
            ResolutionOutcome.not_found,
            candidate_count=1,
            reason=f"CRN matched subject {section.subject}, not expected {expected_subject}.",
        )
    if expected_course is not None and section.course_number != expected_course.strip().upper():
        return HistoricalResolution(
            ResolutionOutcome.not_found,
            candidate_count=1,
            reason=f"CRN matched course {section.course_number}, not expected {expected_course}.",
        )
    return HistoricalResolution(
        ResolutionOutcome.matched,
        section=section,
        candidate_count=1,
    )
