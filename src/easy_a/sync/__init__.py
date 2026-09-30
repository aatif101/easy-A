"""Live USF schedule sync: cadence rules, runner loop and shared vocabulary.

This package root must stay light. The worker and the API both import it, so it imports only
``easy_a.common.terms`` (no pandas, nothing from ``easy_a.refresh``).
"""

from __future__ import annotations

from easy_a.common.terms import normalize_banner_term_code

SYNC_SOURCE_PREFIX = "usf_schedule_sync"

# Fixed vocabulary for the "kind: " prefix of a failed IngestRun.error_message (written by the
# worker) and for the coarse error kind the API reports. Never expose raw error text publicly.
SYNC_ERROR_KINDS: frozenset[str] = frozenset(
    {
        "usf_http",
        "usf_timeout",
        "usf_response",
        "parse",
        "scope",
        "gate",
        "database",
        "schema",
        "unexpected",
    }
)


def sync_source(term: str | int) -> str:
    """IngestRun.source for sweeps of one term (IngestRun has no term column)."""
    return f"{SYNC_SOURCE_PREFIX}:{normalize_banner_term_code(term)}"
