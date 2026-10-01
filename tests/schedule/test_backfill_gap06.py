"""Phase 10 gap 06: campus gate before normalisation, row quarantine, response saving and replay.

Everything runs over SQLite and a fake USF client or saved pages written by the tests themselves;
nothing touches a live service, and the replay tests prove no HTTP client is ever built.
"""

from __future__ import annotations

import json
import stat
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.db import Base
from easy_a.models import Course, Term
from easy_a.schedule import backfill_cli
from easy_a.schedule.backfill import (
    ROW_FAILURE_REPORT_LIMIT,
    backfill_row_gate,
    select_backfill_rows,
)
from easy_a.schedule.backfill_cli import (
    FAILED_RESPONSE_DIR,
    REPO_ROOT,
    _guard_failures,
    _responses_dir,
    _saved_dir,
    main,
)
from easy_a.schedule.client import StaffScheduleClient
from easy_a.schedule.normalize import RowFailure, SkippedRow
from easy_a.sync.fetch import parse_whole_term
from tests.schedule.test_backfill import add_grade, per_term_handler, run
from tests.sync.sweep_support import table_counts, usf_client
from tests.sync.wholeterm_html import RowSpec, build_whole_term_html


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    with Session(eng) as session:
        session.add_all(
            [
                Term(id=1, banner_code="202701", name="Spring 2027", year=2027, season="Spring"),
                Term(id=2, banner_code="202408", name="Fall 2024", year=2024, season="Fall"),
                Term(id=3, banner_code="202501", name="Spring 2025", year=2025, season="Spring"),
                Course(
                    id=10,
                    subject="MAC",
                    number="1105",
                    title="College Algebra",
                    catalog_edition="2026-2027",
                ),
                Course(
                    id=11,
                    subject="ENC",
                    number="1101",
                    title="Composition I",
                    catalog_edition="2026-2027",
                ),
            ]
        )
        session.commit()
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


# CRN -> (campus, time cell, graded). 89035 is on an excluded campus with a cell no normaliser
# accepts; 89034's two unscheduled components are valid since the normaliser change.
GRADED = ("89033", "89034", "89035", "89036")


def mixed_rows() -> list[RowSpec]:
    return [
        RowSpec(crn="89033", campus="Tampa", instructor="I. Rothstein"),
        RowSpec(
            crn="89034",
            subject="ENC",
            number="1101",
            title="Composition I",
            campus="Off-campus - Tampa",
            time="TBA TBA",
        ),
        RowSpec(crn="89035", campus="Sarasota-Manatee", time="not a time"),
        RowSpec(crn="89036", campus="St. Petersburg"),
        RowSpec(crn="89100", campus="Tampa", instructor="A. Other"),  # not graded
        RowSpec(crn="89101", campus="Mystery Campus"),  # not graded
    ]


def seed_grades(session_factory: sessionmaker[Session], crns: tuple[str, ...] = GRADED) -> None:
    for crn in crns:
        add_grade(
            session_factory,
            term_id=2,
            crn=crn,
            course_id=11 if crn == "89034" else 10,
        )


def serve(html_by_term: dict[str, str]) -> tuple[Callable[[], StaffScheduleClient], list[Any]]:
    client, requests = usf_client(handler=per_term_handler(html_by_term))
    return (lambda: client), requests


def page(rows: list[RowSpec]) -> str:
    return build_whole_term_html(rows, error_tail=False)


# --- campus gate before normalisation: the selection counts do not depend on it ------------------


def test_selection_counts_are_identical_with_the_gate_before_or_after_normalisation() -> None:
    rows = [r for r in mixed_rows() if r.crn != "89035"]  # every shape the old path can read
    html = page(rows)
    grade_keys = {
        "89033": frozenset({("MAC", "1105")}),
        "89034": frozenset({("ENC", "1101")}),
        "89036": frozenset({("MAC", "1105")}),
        "89200": frozenset({("MAC", "1105")}),  # graded, absent from the page: unmatched
    }
    course_ids = {("MAC", "1105"): 10, ("ENC", "1101"): 11}

    ungated = parse_whole_term(html)
    gated = parse_whole_term(html, row_gate=backfill_row_gate, quarantine_row_failures=True)
    before = select_backfill_rows("202408", ungated.rows, grade_keys, course_ids)
    after = select_backfill_rows(
        "202408", gated.rows, grade_keys, course_ids, skipped=gated.skipped, failures=gated.failures
    )

    assert gated.skipped and len(gated.rows) < len(ungated.rows)
    assert after == before  # every field: counts, histograms, campus breakdown, rows to write
    assert after.fetched_rows == ungated.data_row_count
    assert after.non_tampa == 1 and after.non_tampa_by_label == {"St. Petersburg": 1}
    assert after.not_graded == 2 and after.unmatched_grade_crns == 1
    assert dict(after.unknown_campus_labels) == {}


def test_a_skipped_row_on_an_allowed_campus_is_a_bug_and_raises() -> None:
    from easy_a.schedule.backfill import BackfillGuardError

    with pytest.raises(BackfillGuardError):
        select_backfill_rows("202408", (), {}, {}, skipped=[SkippedRow(crn="1", campus="Tampa")])


def test_quarantined_rows_are_fetched_and_campus_counted_but_never_written() -> None:
    failure = RowFailure(position=4, crn="89033", campus="Tampa", field="time", shape="? ?")
    grade_keys = {"89033": frozenset({("MAC", "1105")}), "89300": frozenset({("MAC", "1105")})}
    selection = select_backfill_rows(
        "202408", (), grade_keys, {("MAC", "1105"): 10}, failures=[failure]
    )

    assert selection.fetched_rows == 1
    assert selection.row_normalisation_failures == 1
    assert selection.to_write == 0
    assert selection.rows_by_campus == {"Tampa": 1}
    assert selection.campus_allowed_rows == 1
    assert selection.not_graded == 0 and selection.non_tampa == 0
    assert selection.matched_grade_rows == 0
    assert selection.unmatched_grade_crns == 1  # 89300 only: the quarantined CRN was fetched


def test_row_normalisation_failures_is_a_guard_failure_and_other_counts_are_not() -> None:
    clean = select_backfill_rows("202408", (), {"1": frozenset({("MAC", "1105")})}, {})
    bad = select_backfill_rows(
        "202408",
        (),
        {},
        {},
        failures=[RowFailure(position=0, crn="1", campus="Tampa", field="time", shape="?")],
    )
    assert _guard_failures(clean, 1.0) == ["zero_rows"]
    assert "row_normalisation_failures" in _guard_failures(bad, 1.0)


# --- backfill CLI: the excluded-campus row can no longer abort a run -----------------------------


def test_an_unreadable_row_on_an_excluded_campus_no_longer_aborts_and_is_counted_as_non_tampa(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_grades(session_factory)
    client_factory, requests = serve({"202408": page(mixed_rows())})

    code, report = run(["--terms", "202408", "--dry-run"], session_factory, client_factory, capsys)

    assert code == 0, report.get("error")
    assert len(requests) == 1
    term = report["terms"]["202408"]
    assert term["fetched_rows"] == 6
    assert term["non_tampa"] == 2
    assert term["non_tampa_by_label"] == {"Sarasota-Manatee": 1, "St. Petersburg": 1}
    assert term["unknown_campus_labels"] == {}
    assert term["to_write"] == 2  # Tampa 89033 and the TBA TBA Off-campus - Tampa 89034
    assert term["row_normalisation_failures"] == 0
    assert term["row_failures"] == [] and term["row_failures_omitted"] == 0
    assert term["guard_failures"] == []
    assert term["rows_by_campus"] == {
        "Mystery Campus": 1,
        "Off-campus - Tampa": 1,
        "Sarasota-Manatee": 1,
        "St. Petersburg": 1,
        "Tampa": 2,
    }
    assert term["campus_allowed_rows"] == 3


def test_a_placeholder_only_time_row_on_an_allowed_campus_is_written_with_no_time(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    from sqlalchemy import select

    from easy_a.models import Section

    seed_grades(session_factory)
    client_factory, _ = serve({"202408": page(mixed_rows())})

    code, report = run(
        ["--terms", "202408", "--apply", "--rebuild-term", "202701"],
        session_factory,
        client_factory,
        capsys,
    )

    assert code == 0, report.get("error")
    with session_factory() as session:
        sections = {s.crn: s for s in session.scalars(select(Section))}
    assert set(sections) == {"89033", "89034"}
    tba = sections["89034"]
    assert (tba.start_time, tba.end_time) == (None, None)
    assert tba.campus == "Off-campus - Tampa"
    assert sections["89033"].start_time is not None


# --- backfill CLI: per-row quarantine and the row_normalisation_failures guard -------------------


def quarantine_rows(bad: int = 1) -> list[RowSpec]:
    """Two good graded rows plus ``bad`` graded allowed-campus rows with an unreadable time."""
    return [
        RowSpec(crn="89033", instructor="I. Rothstein"),
        RowSpec(crn="89034", subject="ENC", number="1101", title="Composition I"),
        *[
            RowSpec(crn=str(89500 + i), campus="Off-campus - Tampa", time="9am to noon")
            for i in range(bad)
        ],
    ]


def test_dry_run_reports_quarantined_rows_computes_the_rest_and_exits_1(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_grades(session_factory, ("89033", "89034", "89500"))
    before = table_counts(session_factory)
    client_factory, _ = serve({"202408": page(quarantine_rows())})

    code, report = run(["--terms", "202408", "--dry-run"], session_factory, client_factory, capsys)

    assert code == 1
    assert report["status"] == "failed" and report["error_kind"] == "guard"
    assert report["written"] is False
    term = report["terms"]["202408"]
    assert term["guard_failures"] == ["row_normalisation_failures"]
    assert term["row_normalisation_failures"] == 1
    assert term["row_failures"] == [
        {"position": 2, "campus": "Off-campus - Tampa", "field": "time", "shape": "? ? ?"}
    ]
    assert term["row_failures_omitted"] == 0
    # The rest of the term was still computed, including the what-if and the write counts.
    assert term["fetched_rows"] == 3
    assert term["to_write"] == 2 and term["inserted"] == 2
    assert "what_if" in report
    assert table_counts(session_factory) == before  # a dry run never writes
    blob = json.dumps(report)
    assert "9am to noon" not in blob and "://" not in blob


def test_the_report_lists_at_most_the_cap_but_counts_every_failed_row(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    total = ROW_FAILURE_REPORT_LIMIT + 5
    seed_grades(session_factory, ("89033", "89034"))
    client_factory, _ = serve({"202408": page(quarantine_rows(total))})

    code, report = run(["--terms", "202408", "--dry-run"], session_factory, client_factory, capsys)

    term = report["terms"]["202408"]
    assert code == 1
    assert term["row_normalisation_failures"] == total
    assert len(term["row_failures"]) == ROW_FAILURE_REPORT_LIMIT
    assert term["row_failures_omitted"] == 5
    assert [item["position"] for item in term["row_failures"]] == list(range(2, 2 + 10))


def test_apply_refuses_and_writes_nothing_when_an_allowed_row_cannot_be_normalised(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_grades(session_factory, ("89033", "89034", "89500"))
    before = table_counts(session_factory)
    client_factory, _ = serve({"202408": page(quarantine_rows())})

    code, report = run(
        ["--terms", "202408", "--apply", "--rebuild-term", "202701"],
        session_factory,
        client_factory,
        capsys,
    )

    assert code == 1
    assert report["error_kind"] == "guard" and report["written"] is False
    assert report["terms"]["202408"]["guard_failures"] == ["row_normalisation_failures"]
    assert "applied" not in report  # nothing was even attempted
    assert table_counts(session_factory) == before  # not even an IngestRun row


def test_a_bad_row_in_a_later_term_still_stops_apply_for_every_term(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_grades(session_factory, ("89033", "89034"))
    add_grade(session_factory, term_id=3, crn="89600", course_id=10)
    before = table_counts(session_factory)
    pages = {
        "202408": page(quarantine_rows(0)),
        "202501": page([RowSpec(crn="89600", time="not a time")]),
    }
    client_factory, _ = serve(pages)

    code, report = run(
        ["--terms", "202408", "202501", "--apply", "--rebuild-term", "202701"],
        session_factory,
        client_factory,
        capsys,
    )

    assert code == 1
    assert report["terms"]["202408"]["guard_failures"] == []
    assert report["terms"]["202501"]["guard_failures"] == ["row_normalisation_failures"]
    assert table_counts(session_factory) == before


def test_a_failing_ungraded_allowed_row_also_fails_the_guard(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    """Strictness is unchanged: any allowed-campus row that cannot be read fails the run."""
    seed_grades(session_factory, ("89033", "89034"))
    client_factory, _ = serve({"202408": page(quarantine_rows(1))})  # 89500 has no grade row

    code, report = run(["--terms", "202408", "--dry-run"], session_factory, client_factory, capsys)

    assert code == 1
    assert report["terms"]["202408"]["row_normalisation_failures"] == 1


# --- --save-responses ----------------------------------------------------------------------------


def test_save_responses_writes_every_term_as_it_arrives_with_mode_0600(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    seed_grades(session_factory)
    pages = {"202408": page(mixed_rows()), "202501": page([RowSpec(crn="1")])}
    client_factory, _ = serve(pages)
    target = tmp_path / "saved" / "run1"

    code, report = run(
        ["--terms", "202408", "202501", "--dry-run", "--save-responses", str(target)],
        session_factory,
        client_factory,
        capsys,
    )

    assert code == 0, report.get("error")
    assert sorted(p.name for p in target.iterdir()) == ["202408.html", "202501.html"]
    for term, html in pages.items():
        saved = target / f"{term}.html"
        assert saved.read_text(encoding="utf-8") == html
        assert stat.S_IMODE(saved.stat().st_mode) == 0o600
        assert report["saved_responses"][term]["saved"] is True
        assert report["saved_responses"][term]["bytes"] == len(html.encode("utf-8"))
    assert "Rothstein" not in json.dumps(report)


def test_save_responses_is_off_by_default(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    seed_grades(session_factory)
    client_factory, _ = serve({"202408": page(mixed_rows())})
    code, report = run(["--terms", "202408", "--dry-run"], session_factory, client_factory, capsys)
    assert code == 0
    assert "saved_responses" not in report
    assert list(tmp_path.iterdir()) == []


def test_save_responses_keeps_the_pages_that_arrived_before_a_later_failure(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    seed_grades(session_factory)
    good = page(mixed_rows())
    short = build_whole_term_html(
        [RowSpec(crn="1"), RowSpec(crn="2")], error_tail=False, malformed_crns=["2"]
    )
    client_factory, _ = serve({"202408": good, "202501": short})

    code, report = run(
        ["--terms", "202408", "202501", "--dry-run", "--save-responses", str(tmp_path / "d")],
        session_factory,
        client_factory,
        capsys,
    )

    assert code == 1 and report["error_kind"] == "parse" and report["failed_term"] == "202501"
    assert (tmp_path / "d" / "202408.html").read_text(encoding="utf-8") == good
    assert (tmp_path / "d" / "202501.html").read_text(encoding="utf-8") == short
    assert set(report["saved_responses"]) == {"202408", "202501"}


def test_save_responses_resets_the_mode_of_an_existing_file(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    seed_grades(session_factory)
    existing = tmp_path / "202408.html"
    existing.write_text("old")
    existing.chmod(0o644)
    client_factory, _ = serve({"202408": page(mixed_rows())})

    run(
        ["--terms", "202408", "--dry-run", "--save-responses", str(tmp_path)],
        session_factory,
        client_factory,
        capsys,
    )

    assert stat.S_IMODE(existing.stat().st_mode) == 0o600
    assert existing.read_text(encoding="utf-8") != "old"


def test_a_save_error_is_reported_and_does_not_stop_the_run(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    seed_grades(session_factory)
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where a directory is needed")
    client_factory, _ = serve({"202408": page(mixed_rows())})

    code, report = run(
        ["--terms", "202408", "--dry-run", "--save-responses", str(blocker / "sub")],
        session_factory,
        client_factory,
        capsys,
    )

    assert code == 0
    assert report["saved_responses"]["202408"]["saved"] is False
    assert "path" not in report["saved_responses"]["202408"]


def test_save_responses_path_rules_match_save_failed_response(tmp_path: Path) -> None:
    assert _responses_dir(str(tmp_path / "x")) == (tmp_path / "x").resolve()
    assert _responses_dir(str(FAILED_RESPONSE_DIR)) == FAILED_RESPONSE_DIR
    assert _responses_dir(str(FAILED_RESPONSE_DIR / "run1")) == FAILED_RESPONSE_DIR / "run1"
    import argparse

    for refused in (
        REPO_ROOT / "docs",
        REPO_ROOT / "docs" / "saved",
        REPO_ROOT,
        REPO_ROOT / ".planning",
        REPO_ROOT / ".planning" / "phases" / "10-professor-level-grades",
        REPO_ROOT / ".planning" / "phases" / "10-professor-level-grades" / "other",
    ):
        with pytest.raises(argparse.ArgumentTypeError):
            _responses_dir(str(refused))
    existing_file = tmp_path / "f.html"
    existing_file.write_text("x")
    with pytest.raises(argparse.ArgumentTypeError):
        _responses_dir(str(existing_file))


def test_save_responses_is_refused_inside_tracked_paths_before_any_request(
    session_factory: sessionmaker[Session],
) -> None:
    def forbidden() -> StaffScheduleClient:
        raise AssertionError("a refused path must not reach USF")

    code = main(
        ["--terms", "202408", "--dry-run", "--save-responses", str(REPO_ROOT / "docs" / "saved")],
        session_factory=session_factory,
        client_factory=forbidden,
    )
    assert code == 2
    assert not (REPO_ROOT / "docs" / "saved").exists()


def test_save_responses_is_refused_for_modes_that_make_no_request(
    session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    for mode in (["--rollback"], ["--rebuild-only"]):
        code = main(
            [*mode, "--rebuild-term", "202701", "--save-responses", str(tmp_path / "x")],
            session_factory=session_factory,
        )
        assert code == 2


# --- --from-saved replay: identical pipeline, zero requests --------------------------------------


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Any attempt to build or use an HTTP client fails the test and is recorded."""
    attempts: list[str] = []

    def fail(name: str) -> Callable[..., Any]:
        def inner(*_args: Any, **_kwargs: Any) -> Any:
            attempts.append(name)
            raise AssertionError(f"network access attempted: {name}")

        return inner

    monkeypatch.setattr(backfill_cli, "StaffScheduleClient", fail("StaffScheduleClient"))
    monkeypatch.setattr(httpx.Client, "__init__", fail("httpx.Client()"))
    monkeypatch.setattr(httpx.Client, "send", fail("httpx.Client.send"))
    monkeypatch.setattr(httpx.Client, "stream", fail("httpx.Client.stream"))
    monkeypatch.setattr(httpx, "post", fail("httpx.post"))
    monkeypatch.setattr(httpx, "get", fail("httpx.get"))
    return attempts


def write_saved(directory: Path, pages: dict[str, str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for term, html in pages.items():
        (directory / f"{term}.html").write_text(html, encoding="utf-8")


def test_replay_reproduces_the_report_with_no_client_and_no_request(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_grades(session_factory)
    pages = {"202408": page(mixed_rows())}
    # 1. A normal dry run that also saves its responses.
    client_factory, requests = serve(pages)
    code, live = run(
        ["--terms", "202408", "--dry-run", "--save-responses", str(tmp_path / "saved")],
        session_factory,
        client_factory,
        capsys,
    )
    assert code == 0 and len(requests) == 1
    before = table_counts(session_factory)

    # 2. The replay: no client factory is given, and every way to reach HTTP is booby-trapped.
    attempts: list[str] = []

    def fail(name: str) -> Callable[..., Any]:
        def inner(*_a: Any, **_k: Any) -> Any:
            attempts.append(name)
            raise AssertionError(name)

        return inner

    monkeypatch.setattr(backfill_cli, "StaffScheduleClient", fail("StaffScheduleClient"))
    monkeypatch.setattr(httpx.Client, "__init__", fail("httpx.Client()"))
    sleeps: list[float] = []
    code, replay = run(
        ["--terms", "202408", "--dry-run", "--from-saved", str(tmp_path / "saved")],
        session_factory,
        client_factory=None,  # type: ignore[arg-type]
        capsys=capsys,
        sleeps=sleeps,
    )

    assert code == 0, replay.get("error")
    assert attempts == [] and sleeps == []
    assert len(requests) == 1  # still only the one request from step 1
    assert replay["terms"] == live["terms"]  # counts, campus breakdown, response_bytes, writes
    assert replay["what_if"] == live["what_if"]
    assert replay["request"] == {
        "source": "saved_responses",
        "requests_made": 0,
        "campus_allow_list": live["request"]["campus_allow_list"],
    }
    assert table_counts(session_factory) == before  # a replay writes nothing


def test_replay_never_calls_a_client_factory_it_is_given(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    no_network: list[str],
) -> None:
    seed_grades(session_factory)
    write_saved(tmp_path, {"202408": page(mixed_rows())})
    calls: list[int] = []

    def factory() -> StaffScheduleClient:
        calls.append(1)
        raise AssertionError("the replay must not construct a client")

    code, report = run(
        ["--terms", "202408", "--dry-run", "--from-saved", str(tmp_path)],
        session_factory,
        factory,
        capsys,
    )

    assert code == 0 and calls == [] and no_network == []
    assert report["terms"]["202408"]["response_bytes"] > 0
    assert report["fetch_seconds"] == {"202408": 0.0}


def test_replay_can_replay_a_subset_of_the_saved_terms(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    no_network: list[str],
) -> None:
    seed_grades(session_factory)
    write_saved(tmp_path, {"202408": page(mixed_rows()), "202501": "not even html"})

    code, report = run(
        ["--terms", "202408", "--dry-run", "--from-saved", str(tmp_path)],
        session_factory,
        None,  # type: ignore[arg-type]
        capsys,
    )

    assert code == 0 and list(report["terms"]) == ["202408"] and no_network == []


def test_replay_reports_a_quarantined_row_exactly_like_a_live_dry_run(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    no_network: list[str],
) -> None:
    seed_grades(session_factory, ("89033", "89034", "89500"))
    write_saved(tmp_path, {"202408": page(quarantine_rows())})

    code, report = run(
        ["--terms", "202408", "--dry-run", "--from-saved", str(tmp_path)],
        session_factory,
        None,  # type: ignore[arg-type]
        capsys,
    )

    assert code == 1 and report["error_kind"] == "guard"
    assert report["terms"]["202408"]["row_failures"][0]["field"] == "time"
    assert no_network == []


def test_replay_missing_page_fails_closed_without_a_request(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    no_network: list[str],
) -> None:
    seed_grades(session_factory)
    write_saved(tmp_path, {"202408": page(mixed_rows())})
    before = table_counts(session_factory)

    code, report = run(
        ["--terms", "202408", "202501", "--dry-run", "--from-saved", str(tmp_path)],
        session_factory,
        None,  # type: ignore[arg-type]
        capsys,
    )

    assert code == 1
    assert report["error_kind"] == "saved_response_missing"
    assert report["failed_term"] == "202501" and report["written"] is False
    assert no_network == [] and table_counts(session_factory) == before


def test_replay_of_a_lost_rows_page_reports_the_parse_diagnostics(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    no_network: list[str],
) -> None:
    seed_grades(session_factory)
    short = build_whole_term_html(
        [RowSpec(crn="1"), RowSpec(crn="2")], error_tail=False, malformed_crns=["2"]
    )
    write_saved(tmp_path, {"202408": short})

    code, report = run(
        ["--terms", "202408", "--dry-run", "--from-saved", str(tmp_path)],
        session_factory,
        None,  # type: ignore[arg-type]
        capsys,
    )

    assert code == 1 and report["error_kind"] == "parse"
    assert report["parse_diagnostics"]["suspect_rows"][0]["position"] == 1
    assert no_network == []


@pytest.mark.parametrize(
    "extra",
    [
        ["--apply", "--rebuild-term", "202701"],
        ["--rollback", "--rebuild-term", "202701"],
        ["--rebuild-only", "--rebuild-term", "202701"],
    ],
    ids=["apply", "rollback", "rebuild-only"],
)
def test_from_saved_is_refused_with_every_mode_but_dry_run(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
    no_network: list[str],
    extra: list[str],
) -> None:
    write_saved(tmp_path, {"202408": page(mixed_rows())})
    before = table_counts(session_factory)

    code = main(
        ["--terms", "202408", *extra, "--from-saved", str(tmp_path)],
        session_factory=session_factory,
    )

    assert code == 2
    assert no_network == [] and table_counts(session_factory) == before


def test_from_saved_cannot_be_combined_with_the_save_options(
    session_factory: sessionmaker[Session], tmp_path: Path, no_network: list[str]
) -> None:
    write_saved(tmp_path, {"202408": page(mixed_rows())})
    for option in ("--save-responses", "--save-failed-response"):
        code = main(
            ["--dry-run", "--terms", "202408", "--from-saved", str(tmp_path)]
            + [option, str(tmp_path / "out")],
            session_factory=session_factory,
        )
        assert code == 2, option
    assert sorted(p.name for p in tmp_path.iterdir()) == ["202408.html"]


def test_from_saved_needs_an_existing_directory(
    session_factory: sessionmaker[Session], tmp_path: Path, no_network: list[str]
) -> None:
    import argparse

    with pytest.raises(argparse.ArgumentTypeError):
        _saved_dir(str(tmp_path / "missing"))
    assert (
        main(
            ["--dry-run", "--from-saved", str(tmp_path / "missing")],
            session_factory=session_factory,
        )
        == 2
    )
    assert no_network == []


def test_help_lists_the_new_flags(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    text = capsys.readouterr().out
    assert "--save-responses" in text and "--from-saved" in text
