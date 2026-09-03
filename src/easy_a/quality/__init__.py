"""Typed data-quality checks and reports for Easy-A source data."""

from easy_a.quality.checks import (
    DEFAULT_STALE_AFTER_DAYS,
    SeatValues,
    SectionIdentity,
    check_duplicate_section_identities,
    check_seat_values,
    run_quality_checks,
)
from easy_a.quality.models import FindingSeverity, QualityFinding, QualityReport

__all__ = [
    "DEFAULT_STALE_AFTER_DAYS",
    "FindingSeverity",
    "QualityFinding",
    "QualityReport",
    "SeatValues",
    "SectionIdentity",
    "check_duplicate_section_identities",
    "check_seat_values",
    "run_quality_checks",
]
