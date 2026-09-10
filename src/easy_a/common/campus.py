"""The campus Easy-A supports, and how stored campus labels are compared to it.

The schedule query pins the Banner campus code ``T``; the schedule rows that come back
spell the campus out, so stored ``Section.campus`` values read ``Tampa`` rather than ``T``.
Comparison strips surrounding whitespace and ignores case, because the label is source
text rather than a controlled code.

One definition, imported by both the cleanup command and the quality checks, so a stored
row cannot be in scope for one and out of scope for the other.
"""

from __future__ import annotations

SUPPORTED_CAMPUS = "Tampa"


def same_campus(stored: str, expected: str) -> bool:
    """Whether a stored campus label denotes ``expected``."""
    return stored.strip().casefold() == expected.strip().casefold()


def describe_campus(stored: str) -> str:
    """Render a stored campus label for a human-readable finding."""
    return stored.strip() or "(blank)"
