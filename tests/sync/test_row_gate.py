"""The opt-in pre-normalisation gate and quarantine of ``parse_whole_term`` (Phase 10 gap 06).

Both exist for the one-off backfill only. These tests pin that the default path, which is the live
sync's, still normalises every row first and still fails on a bad row, and that the live sweep
never passes the new parameters.
"""

from __future__ import annotations

import inspect
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker

from easy_a.schedule.backfill import backfill_row_gate
from easy_a.schedule.parser import ParsedScheduleRow, ScheduleParseError
from easy_a.sync import sweep as sweep_module
from easy_a.sync.fetch import fetch_whole_term, parse_saved_term, parse_whole_term
from easy_a.sync.runner import SweepStatus
from easy_a.sync.sweep import run_sweep
from tests.sync.sweep_support import SWEEP_AT, TERM, enc_rows, seed_from_rows, usf_client
from tests.sync.wholeterm_html import RowSpec, build_whole_term_html

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

# One row per outcome: fine; a bad time cell on an excluded campus; a bad capacity cell on an
# allowed campus; a placeholder-only time cell (now valid) on an excluded campus.
GOOD = RowSpec(crn="10001", campus="Tampa")
EXCLUDED_BAD_TIME = RowSpec(crn="10002", campus="Sarasota-Manatee", time="not a time")
ALLOWED_BAD_CAP = RowSpec(crn="10003", campus="Off-campus - Tampa", capacity_raw="twelve")
EXCLUDED_TBA_TBA = RowSpec(crn="10004", campus="Sarasota-Manatee", time="TBA TBA")


def _page(*specs: RowSpec) -> str:
    return build_whole_term_html(list(specs), error_tail=False)


def test_default_path_still_normalises_every_row_first_and_fails_on_a_bad_row() -> None:
    # The excluded-campus row would be dropped by any campus gate, but the default path has none.
    with pytest.raises(ScheduleParseError, match="Invalid schedule time range"):
        parse_whole_term(_page(GOOD, EXCLUDED_BAD_TIME))
    with pytest.raises(ScheduleParseError, match="Invalid capacity value"):
        parse_whole_term(_page(GOOD, ALLOWED_BAD_CAP))


def test_default_path_result_has_no_skipped_or_failed_rows() -> None:
    parsed = parse_whole_term(_page(GOOD, EXCLUDED_TBA_TBA))
    assert len(parsed.rows) == parsed.data_row_count == 2
    assert parsed.skipped == ()
    assert parsed.failures == ()
    # Every row, whatever its campus, is a normalised row on the default path.
    assert [row.campus for row in parsed.rows] == ["Tampa", "Sarasota-Manatee"]
    assert parsed.rows[1].start_time is None and parsed.rows[1].end_time is None


def test_the_new_parameters_default_off_everywhere_the_live_sync_calls() -> None:
    for function in (parse_whole_term, fetch_whole_term):
        parameters = inspect.signature(function).parameters
        assert parameters["row_gate"].default is None
        assert parameters["quarantine_row_failures"].default is False
    assert inspect.signature(fetch_whole_term).parameters["on_response"].default is None
    assert "client" not in inspect.signature(parse_saved_term).parameters  # a replay has no client


def test_live_sweep_never_passes_the_gate_quarantine_or_response_hook(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[dict[str, Any]] = []
    real = sweep_module.fetch_whole_term

    def recording(*args: Any, **kwargs: Any) -> Any:
        seen.append(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(sweep_module, "fetch_whole_term", recording)
    rows = [RowSpec(crn="13173", instructor="J. Doe"), *enc_rows(19)]
    seed_from_rows(session_factory, rows)
    client, _requests = usf_client(build_whole_term_html(rows))
    outcome = run_sweep(session_factory, term=TERM, client=client, now_fn=lambda: SWEEP_AT)

    assert outcome.status is SweepStatus.succeeded
    assert len(seen) == 1
    for name in ("row_gate", "quarantine_row_failures", "on_response", "on_parse_failure"):
        assert name not in seen[0]
    assert "campus" not in seen[0]  # still the default campus=T


def test_live_sweep_still_fails_on_an_unnormalisable_row_even_on_another_campus(
    session_factory: sessionmaker[Session],
) -> None:
    rows = [RowSpec(crn="13173", instructor="J. Doe"), *enc_rows(19)]
    seed_from_rows(session_factory, rows)
    bad = [*rows, RowSpec(crn="99001", campus="Sarasota-Manatee", time="not a time")]
    client, _requests = usf_client(build_whole_term_html(bad))

    outcome = run_sweep(session_factory, term=TERM, client=client, now_fn=lambda: SWEEP_AT)

    assert outcome.status is SweepStatus.failed
    assert outcome.error_kind == "parse"


def test_a_placeholder_only_time_cell_no_longer_fails_the_live_sweep(
    session_factory: sessionmaker[Session],
) -> None:
    """The one shared-code behaviour change (normaliser): ``TBA TBA`` is no time, not an error."""
    rows = [RowSpec(crn="13173", instructor="J. Doe"), *enc_rows(19)]
    seed_from_rows(session_factory, rows)
    changed = [replace(rows[0], time="TBA TBA"), *rows[1:]]
    client, _requests = usf_client(build_whole_term_html(changed))

    outcome = run_sweep(session_factory, term=TERM, client=client, now_fn=lambda: SWEEP_AT)

    assert outcome.status is SweepStatus.succeeded


def test_the_gate_sets_a_row_aside_before_it_is_normalised() -> None:
    parsed = parse_whole_term(
        _page(GOOD, EXCLUDED_BAD_TIME, EXCLUDED_TBA_TBA), row_gate=backfill_row_gate
    )
    assert parsed.data_row_count == 3
    assert [row.crn for row in parsed.rows] == ["10001"]
    assert [(item.crn, item.campus) for item in parsed.skipped] == [
        ("10002", "Sarasota-Manatee"),
        ("10004", "Sarasota-Manatee"),
    ]
    assert parsed.failures == ()


def test_the_gate_alone_is_enough_for_a_bad_row_on_an_excluded_campus() -> None:
    """Even a shape no normaliser accepts is never read when its campus is excluded."""
    parsed = parse_whole_term(_page(EXCLUDED_BAD_TIME), row_gate=backfill_row_gate)
    assert parsed.rows == ()
    assert len(parsed.skipped) == 1


def test_an_allowed_row_that_fails_still_raises_unless_quarantine_is_asked_for() -> None:
    with pytest.raises(ScheduleParseError, match="Invalid capacity value"):
        parse_whole_term(_page(GOOD, ALLOWED_BAD_CAP), row_gate=backfill_row_gate)


def test_quarantine_collects_position_campus_field_and_shape_and_keeps_going() -> None:
    parsed = parse_whole_term(
        _page(GOOD, EXCLUDED_BAD_TIME, ALLOWED_BAD_CAP, RowSpec(crn="10005", time="not a time")),
        row_gate=backfill_row_gate,
        quarantine_row_failures=True,
    )
    assert [row.crn for row in parsed.rows] == ["10001"]
    assert [(f.position, f.crn, f.campus, f.field, f.shape) for f in parsed.failures] == [
        (2, "10003", "Off-campus - Tampa", "capacity", "non_integer"),
        (3, "10005", "Tampa", "time", "? ? ?"),
    ]
    assert len(parsed.skipped) == 1
    # Fingerprints carry structure only: none of the cell text can be recovered from them.
    assert "twelve" not in repr(parsed.failures)
    assert "not a time" not in repr(parsed.failures)


def test_quarantine_without_a_gate_collects_every_failing_row() -> None:
    parsed = parse_whole_term(
        _page(GOOD, EXCLUDED_BAD_TIME, ALLOWED_BAD_CAP), quarantine_row_failures=True
    )
    assert [f.crn for f in parsed.failures] == ["10002", "10003"]
    assert parsed.skipped == ()


def test_the_lost_rows_guard_runs_over_every_row_whatever_the_gate_says() -> None:
    html = build_whole_term_html(
        [GOOD, EXCLUDED_BAD_TIME], error_tail=False, malformed_crns=["10002"]
    )
    with pytest.raises(ScheduleParseError, match="silently lost rows"):
        parse_whole_term(html, row_gate=backfill_row_gate, quarantine_row_failures=True)


def test_gate_is_called_with_the_parsed_row() -> None:
    calls: list[ParsedScheduleRow] = []

    def gate(row: ParsedScheduleRow) -> bool:
        calls.append(row)
        return True

    parse_whole_term(_page(GOOD, EXCLUDED_TBA_TBA), row_gate=gate)
    assert [row.crn for row in calls] == ["10001", "10004"]
