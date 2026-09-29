"""Pure sweep sanity gate: decide whether a scoped response may be applied to the database.

The real whole-term response always ends in a USF error tail, so a missing footer is not a signal.
The gate keys on row counts and subject coverage against what the database already holds. It
compares scoped (in-scope) rows only, so a response that adds sections never trips it.

This module must stay light: no pandas, nothing from ``easy_a.refresh``, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class GateInput:
    in_scope_rows: int
    db_active_in_scope: int
    missing_active: int
    last_success_records_seen: int | None
    db_active_subjects: frozenset[str]
    sweep_subjects: frozenset[str]


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reasons: tuple[str, ...]


def _exact(value: float) -> Fraction:
    """Exact decimal reading of a threshold, so boundaries are not decided by float error."""
    return Fraction(str(value))


def evaluate_gate(
    inp: GateInput,
    *,
    max_missing_fraction: float = 0.10,
    min_row_ratio: float = 0.90,
    max_absent_subject_fraction: float = 0.02,
    min_absent_subjects: int = 2,
) -> GateResult:
    """Return every failed rule; the sweep may write only when ``passed`` is true."""
    reasons: list[str] = []

    if inp.in_scope_rows == 0:
        reasons.append("zero_rows")

    if inp.db_active_in_scope > 0:
        limit = _exact(max_missing_fraction) * inp.db_active_in_scope
        if inp.missing_active > limit:
            fraction = inp.missing_active / inp.db_active_in_scope
            reasons.append(
                f"missing_fraction {fraction:.3f} above {max_missing_fraction:.3f} "
                f"({inp.missing_active} of {inp.db_active_in_scope} active sections missing)"
            )

    if inp.last_success_records_seen is not None:
        floor = _exact(min_row_ratio) * inp.last_success_records_seen
        if inp.in_scope_rows < floor:
            reasons.append(
                f"row_floor {inp.in_scope_rows} below {min_row_ratio:.0%} of "
                f"{inp.last_success_records_seen}"
            )

    absent = sorted(inp.db_active_subjects - inp.sweep_subjects)
    subject_limit = max(
        min_absent_subjects,
        int(_exact(max_absent_subject_fraction) * len(inp.db_active_subjects)),
    )
    if len(absent) > subject_limit:
        shown = ", ".join(absent[:10])
        reasons.append(f"subjects_absent {len(absent)} above {subject_limit}: {shown}")

    return GateResult(passed=not reasons, reasons=tuple(reasons))
