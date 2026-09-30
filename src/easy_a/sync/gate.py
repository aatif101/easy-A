"""Pure sweep sanity gate: decide whether a scoped response may be applied to the database.

The real whole-term response always ends in a USF error tail, so a missing footer is not a signal.
The gate keys on row counts and subject coverage against what the database already holds. It
compares scoped (in-scope) rows only, so a response that adds sections never trips it.

The one operator override (``--max-missing-fraction``) is mapped onto every size rule by
``gate_thresholds``. It is operator-only, available with ``--once``/``--dry-run`` only, and never
used by the worker loop, which always evaluates the gate at the defaults.

This module must stay light: no pandas, nothing from ``easy_a.refresh``, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

DEFAULT_MAX_MISSING_FRACTION = 0.10
DEFAULT_MIN_ROW_RATIO = 0.90
DEFAULT_MAX_ABSENT_SUBJECT_FRACTION = 0.02
DEFAULT_MIN_ABSENT_SUBJECTS = 2


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


@dataclass(frozen=True)
class GateThresholds:
    """The four keyword thresholds of ``evaluate_gate``; the defaults are today's gate."""

    max_missing_fraction: float = DEFAULT_MAX_MISSING_FRACTION
    min_row_ratio: float = DEFAULT_MIN_ROW_RATIO
    max_absent_subject_fraction: float = DEFAULT_MAX_ABSENT_SUBJECT_FRACTION
    min_absent_subjects: int = DEFAULT_MIN_ABSENT_SUBJECTS


def gate_thresholds(override: float | None) -> GateThresholds:
    """Map the one operator fraction onto every size rule (``None`` is the unchanged default).

    The override is the largest share of the term the operator accepts losing. At or below the
    default it only changes the missing-sections limit. Above it, the row floor becomes
    ``1 - override`` of the last succeeded sweep and the absent-subject limit becomes ``override``
    of the subjects. ``zero_rows`` has no threshold, so no override can clear it.
    """
    if override is None:
        return GateThresholds()
    if not 0 <= _exact(override) <= 1:
        raise ValueError(f"gate override must be between 0 and 1, got {override}")
    if _exact(override) <= _exact(DEFAULT_MAX_MISSING_FRACTION):
        return GateThresholds(max_missing_fraction=override)
    # Exact decimal complement: float 1.0 - 0.7 is 0.30000000000000004 and would refuse 300/1000.
    return GateThresholds(
        max_missing_fraction=override,
        min_row_ratio=float(1 - _exact(override)),
        max_absent_subject_fraction=override,
    )


def evaluate_gate(
    inp: GateInput,
    *,
    max_missing_fraction: float = DEFAULT_MAX_MISSING_FRACTION,
    min_row_ratio: float = DEFAULT_MIN_ROW_RATIO,
    max_absent_subject_fraction: float = DEFAULT_MAX_ABSENT_SUBJECT_FRACTION,
    min_absent_subjects: int = DEFAULT_MIN_ABSENT_SUBJECTS,
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
