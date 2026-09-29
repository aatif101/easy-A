"""D-04 sweep scope: undergraduate Tampa rows, plus the D-03 breakdown of what was dropped.

``is_undergraduate_number`` is the single home of the undergraduate rule (first four course
number characters are digits below 5000) so widening or narrowing it later is a one-place change.

This module must stay light: no pandas and nothing from ``easy_a.refresh``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from easy_a.common.campus import SUPPORTED_CAMPUS, same_campus
from easy_a.schedule.normalize import NormalizedSection

UNDERGRADUATE_CEILING = 5000
_MAX_REPORTED_DUPLICATES = 10


class SweepScopeError(ValueError):
    """Raised when in-scope rows violate an identity guard (duplicate CRN)."""


def _has_numeric_prefix(number: str) -> bool:
    prefix = number[:4]
    return len(prefix) == 4 and prefix.isascii() and prefix.isdigit()


def is_undergraduate_number(number: str) -> bool:
    """True when the first four characters are digits and their value is below 5000."""
    return _has_numeric_prefix(number) and int(number[:4]) < UNDERGRADUATE_CEILING


@dataclass(frozen=True)
class ScopeReport:
    total_rows: int
    distinct_crns: int
    non_tampa_rows: int
    graduate_rows: int
    unparseable_number_rows: int
    in_scope_rows: int
    subjects: frozenset[str]
    course_keys: frozenset[tuple[str, str]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "distinct_crns": self.distinct_crns,
            "non_tampa_rows": self.non_tampa_rows,
            "graduate_rows": self.graduate_rows,
            "unparseable_number_rows": self.unparseable_number_rows,
            "in_scope_rows": self.in_scope_rows,
            "subjects": len(self.subjects),
            "course_keys": len(self.course_keys),
        }


def apply_scope(
    rows: Iterable[NormalizedSection],
) -> tuple[tuple[NormalizedSection, ...], ScopeReport]:
    """Keep undergraduate Tampa rows; raise on a duplicate CRN among them."""
    total = 0
    crns: set[str] = set()
    non_tampa = 0
    graduate = 0
    unparseable = 0
    in_scope: list[NormalizedSection] = []
    for row in rows:
        total += 1
        crns.add(row.crn)
        if not same_campus(row.campus, SUPPORTED_CAMPUS):
            non_tampa += 1
            continue
        if not _has_numeric_prefix(row.course_number):
            unparseable += 1
            continue
        if not is_undergraduate_number(row.course_number):
            graduate += 1
            continue
        in_scope.append(row)

    counts = Counter(row.crn for row in in_scope)
    duplicates = sorted(crn for crn, count in counts.items() if count > 1)
    if duplicates:
        listed = ", ".join(duplicates[:_MAX_REPORTED_DUPLICATES])
        raise SweepScopeError(
            f"Sweep contains {len(duplicates)} duplicate in-scope CRN(s): {listed}"
        )

    report = ScopeReport(
        total_rows=total,
        distinct_crns=len(crns),
        non_tampa_rows=non_tampa,
        graduate_rows=graduate,
        unparseable_number_rows=unparseable,
        in_scope_rows=len(in_scope),
        subjects=frozenset(row.subject for row in in_scope),
        course_keys=frozenset((row.subject, row.course_number) for row in in_scope),
    )
    return tuple(in_scope), report
