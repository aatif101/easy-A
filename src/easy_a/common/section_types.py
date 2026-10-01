"""Section-type rules shared by analytics.

This module is the single home of the Laboratory rule (Phase 10 CONTEXT D-13): grades of
laboratory sections never count toward an instructor's (instructor, course) history, and a
current laboratory section is scored from course-level history. Course, subject and global
history keep laboratory grades.

The vocabulary starts as the single normalized value "laboratory" (the 2026-09-28 research
report's wording). Plan 10-07 confirms it against hosted data before anything goes live.
Matching is exact on the normalized value on purpose: combined types such as lecture-plus-lab
stay included, and unknown types are not treated as labs.
"""

from __future__ import annotations

LABORATORY_SECTION_TYPES: frozenset[str] = frozenset({"laboratory"})


def normalize_section_type(value: str | None) -> str:
    """Strip, collapse internal whitespace and casefold; None becomes the empty string."""
    if value is None:
        return ""
    return " ".join(value.split()).casefold()


def is_laboratory_section_type(value: str | None) -> bool:
    """True when the section type is a laboratory type (CONTEXT D-13)."""
    return normalize_section_type(value) in LABORATORY_SECTION_TYPES
