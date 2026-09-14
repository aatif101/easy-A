"""Supported-campus constants and stored-label comparison helpers."""

from __future__ import annotations

SUPPORTED_CAMPUS = "Tampa"


def same_campus(stored: str | None, expected: str) -> bool:
    """Return whether a nonblank stored campus label denotes ``expected``."""
    if stored is None or not stored.strip():
        return False
    return stored.strip().casefold() == expected.strip().casefold()


def describe_campus(stored: str | None) -> str:
    """Render a stored campus label for a human-readable quality finding."""
    if stored is None:
        return "(null)"
    return stored.strip() or "(blank)"
