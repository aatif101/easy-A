"""The one-off historical backfill, end to end over a fake USF client (SQLite, MockTransport)."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable, Generator, Iterable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.analytics.queries import get_instructor_course_historical_outcome_stats
from easy_a.common.lookups import resolve_course_id
from easy_a.db import Base
from easy_a.models import (
    Course,
    GradeDistribution,
    IngestRun,
    SeatSnapshot,
    Section,
    SectionInstructor,
    Term,
)
from easy_a.rankings.cache import SectionRankingCache
from easy_a.schedule.backfill import (
    BACKFILL_SOURCE,
    HISTORICAL_GRADE_TERMS,
    BackfillGuardError,
    TermSelection,
    resolve_course_ids,
    select_backfill_rows,
    write_term_backfill,
)
from easy_a.schedule.backfill_cli import main
from easy_a.schedule.client import StaffScheduleClient
from easy_a.sync import courses as courses_module
from easy_a.sync.courses import CatalogSettings, CourseAdder
from easy_a.sync.fetch import parse_whole_term
from tests.sync.sweep_support import enc_rows, seed_from_rows, sweep_rows, table_counts, usf_client
from tests.sync.wholeterm_html import RowSpec, build_whole_term_html

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

Handler = Callable[[httpx.Request], httpx.Response]


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


def add_grade(
    session_factory: sessionmaker[Session],
    *,
    term_id: int,
    crn: str,
    course_id: int | None,
    source: str = "usf_infocenter",
) -> None:
    with session_factory.begin() as session:
        session.add(
            GradeDistribution(
                term_id=term_id,
                crn=crn,
                course_id=course_id,
                section_number_raw="001",
                a_count=40,
                b_count=30,
                c_count=20,
                d_count=5,
                f_count=5,
                total_grades=100,
                source=source,
                source_hash=f"hash-{term_id}-{crn}-{source}",
            )
        )


def per_term_handler(html_by_term: dict[str, str]) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        form = parse_qs(request.content.decode(), keep_blank_values=True)
        term = form["P_SEMESTER"][0]
        return httpx.Response(
            200,
            text=html_by_term[term],
            headers={"content-type": "text/html; charset=utf-8"},
        )

    return handler


def client_for(
    rows_by_term: dict[str, Iterable[RowSpec]],
) -> tuple[Callable[[], StaffScheduleClient], list[httpx.Request]]:
    html = {
        term: build_whole_term_html(list(rows), error_tail=False)
        for term, rows in rows_by_term.items()
    }
    client, requests = usf_client(handler=per_term_handler(html))
    return (lambda: client), requests


def run(
    argv: list[str],
    session_factory: sessionmaker[Session],
    client_factory: Callable[[], StaffScheduleClient],
    capsys: pytest.CaptureFixture[str],
    *,
    sleeps: list[float] | None = None,
    now: datetime = NOW,
) -> tuple[int, dict[str, Any]]:
    recorded = sleeps if sleeps is not None else []
    code = main(
        argv,
        session_factory=session_factory,
        client_factory=client_factory,
        now_fn=lambda: now,
        sleep=recorded.append,
    )
    out = capsys.readouterr().out
    assert out.count("\n") == 1, "stdout must be exactly one JSON line"
    assert "://" not in out
    return code, json.loads(out)


def count(session_factory: sessionmaker[Session], model: type) -> int:
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(model)) or 0


def seed_tracer(session_factory: sessionmaker[Session]) -> list[RowSpec]:
    add_grade(session_factory, term_id=2, crn="89033", course_id=10)
    add_grade(session_factory, term_id=2, crn="89034", course_id=11)
    return [
        RowSpec(crn="89033", subject="MAC", number="1105", instructor="I. Rothstein"),
        RowSpec(crn="89100", subject="MAC", number="1105", instructor="A. Other"),
        RowSpec(
            crn="89034",
            subject="ENC",
            number="1101",
            title="Composition I",
            instructor="Staff",
        ),
    ]


def test_tracer_one_term_goes_from_whole_term_response_to_joined_rows(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = seed_tracer(session_factory)
    client_factory, requests = client_for({"202408": rows})

    code, report = run(["--terms", "202408", "--apply"], session_factory, client_factory, capsys)

    assert code == 0
    assert len(requests) == 1
    form = parse_qs(requests[0].content.decode(), keep_blank_values=True)
    assert form["P_SEMESTER"] == ["202408"]
    assert form["P_SUBJ"] == [""]
    assert form["P_CAMPUS"] == ["T"]

    with session_factory() as session:
        sections = session.scalars(select(Section).order_by(Section.crn)).all()
        assert [(s.crn, s.term_id, s.removed_at) for s in sections] == [
            ("89033", 2, None),
            ("89034", 2, None),
        ]
        for section in sections:
            instructors = session.scalars(
                select(SectionInstructor).where(SectionInstructor.section_id == section.id)
            ).all()
            assert [i.source for i in instructors] == [BACKFILL_SOURCE]
        assert session.scalar(select(func.count()).select_from(SeatSnapshot)) == 0

        runs = session.scalars(select(IngestRun)).all()
        assert [(r.source, r.status) for r in runs] == [
            ("usf_schedule_backfill:202408", "succeeded")
        ]

        stats = get_instructor_course_historical_outcome_stats(
            session, "MAC", "1105", "I. Rothstein", before_term_code="202701"
        )
        assert stats is not None

    assert report["mode"] == "apply"
    terms = report["terms"]
    assert isinstance(terms, dict)
    term = terms["202408"]
    assert {
        key: term[key]
        for key in (
            "fetched_rows",
            "grade_crns",
            "to_write",
            "inserted",
            "instructor_rows_added",
            "staff_or_blank",
            "unmatched_grade_crns",
        )
    } == {
        "fetched_rows": 3,
        "grade_crns": 2,
        "to_write": 2,
        "inserted": 2,
        "instructor_rows_added": 2,
        "staff_or_blank": 1,
        "unmatched_grade_crns": 0,
    }
    assert term["section_type_histogram"] == {"Class Lecture": 2}


def test_help_lists_the_documented_flags(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    text = capsys.readouterr().out
    for flag in (
        "--terms",
        "--dry-run",
        "--apply",
        "--pause-seconds",
        "--max-unmatched-fraction",
        "--report-json",
    ):
        assert flag in text
    assert HISTORICAL_GRADE_TERMS == ("202408", "202501", "202505", "202508", "202601")


# --- Task 2: idempotence, request policy and fail-closed guards ---------------------------------


@pytest.fixture(autouse=True)
def offline_default_course_adder(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 202701 sweep in these tests must never reach the live catalog."""

    def offline(url: str) -> str:
        raise httpx.ConnectError(f"catalog is offline in tests: {url}")

    monkeypatch.setattr(
        courses_module,
        "_default_adder",
        CourseAdder(
            fetch=offline,
            sleep=lambda seconds: None,
            settings=CatalogSettings(
                catalog_edition="2026-2027",
                catalog_url_template="https://catalog.invalid/{subject}/{number}",
            ),
        ),
    )


def term_of(report: dict[str, Any], term: str = "202408") -> dict[str, Any]:
    terms: dict[str, Any] = report["terms"]
    return dict(terms[term])


def graded_rows(
    session_factory: sessionmaker[Session], *, instructor: str = "I. Rothstein"
) -> list[RowSpec]:
    add_grade(session_factory, term_id=2, crn="89033", course_id=10)
    add_grade(session_factory, term_id=2, crn="89034", course_id=11)
    return [
        RowSpec(crn="89033", subject="MAC", number="1105", instructor=instructor),
        RowSpec(
            crn="89034", subject="ENC", number="1101", title="Composition I", instructor="Staff"
        ),
    ]


def table_sizes(session_factory: sessionmaker[Session]) -> dict[str, int]:
    return {
        model.__name__: count(session_factory, model)
        for model in (Section, SectionInstructor, SeatSnapshot, IngestRun, SectionRankingCache)
    }


def test_rerun_over_identical_data_changes_nothing(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = graded_rows(session_factory)
    client_factory, _ = client_for({"202408": rows})
    run(["--terms", "202408", "--apply"], session_factory, client_factory, capsys)
    before = table_sizes(session_factory)

    later = NOW + timedelta(days=1)
    code, report = run(
        ["--terms", "202408", "--apply"], session_factory, client_factory, capsys, now=later
    )

    assert code == 0
    term = term_of(report)
    assert (term["inserted"], term["updated"], term["instructor_rows_added"]) == (0, 0, 0)
    assert (term["unchanged"], term["refreshed_last_seen"], term["instructor_changes"]) == (2, 2, 0)
    after = table_sizes(session_factory)
    assert after["Section"] == before["Section"] == 2
    assert after["SectionInstructor"] == before["SectionInstructor"] == 2
    assert after["SeatSnapshot"] == 0
    with session_factory() as session:
        marks = session.scalars(select(Section.last_seen_at)).all()
        assert {m.replace(tzinfo=None) for m in marks} == {later.replace(tzinfo=None)}
        assert session.scalars(select(Section.removed_at)).all() == [None, None]


def test_changed_instructor_appends_one_row_and_changed_field_counts_as_update(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = graded_rows(session_factory)
    first, _ = client_for({"202408": rows})
    run(["--terms", "202408", "--apply"], session_factory, first, capsys)

    changed = [
        RowSpec(crn="89033", subject="MAC", number="1105", instructor="J. Newname"),
        RowSpec(
            crn="89034",
            subject="ENC",
            number="1101",
            title="Composition I",
            instructor="Staff",
            delivery="AD",
        ),
    ]
    second, _ = client_for({"202408": changed})
    code, report = run(
        ["--terms", "202408", "--apply"],
        session_factory,
        second,
        capsys,
        now=NOW + timedelta(days=1),
    )

    assert code == 0
    term = term_of(report)
    assert term["inserted"] == 0
    assert term["updated"] == 1
    assert term["instructor_changes"] == 1
    assert term["instructor_rows_added"] == 1
    assert count(session_factory, SectionInstructor) == 3
    with session_factory() as session:
        delivery = session.scalar(select(Section.delivery_method).where(Section.crn == "89034"))
        assert delivery == "AD"

    # Whitespace and case differences are not a change.
    cosmetic = [
        RowSpec(crn="89033", subject="MAC", number="1105", instructor="  j.   NEWNAME "),
        changed[1],
    ]
    third, _ = client_for({"202408": cosmetic})
    _, report = run(
        ["--terms", "202408", "--apply"],
        session_factory,
        third,
        capsys,
        now=NOW + timedelta(days=2),
    )
    assert term_of(report)["instructor_rows_added"] == 0
    assert count(session_factory, SectionInstructor) == 3


def test_dry_run_reports_apply_counts_and_changes_nothing(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = graded_rows(session_factory)
    client_factory, _ = client_for({"202408": rows})
    before = table_counts(session_factory)

    code, dry = run(["--terms", "202408", "--dry-run"], session_factory, client_factory, capsys)

    assert code == 0
    assert dry["mode"] == "dry_run"
    assert table_counts(session_factory) == before
    assert before["Section"] == before["SeatSnapshot"] == before["IngestRun"] == 0

    _, applied = run(["--terms", "202408", "--apply"], session_factory, client_factory, capsys)
    assert term_of(dry) == term_of(applied)
    assert table_counts(session_factory)["Section"] == 2


@pytest.mark.parametrize("term", ["202701", "202605", "202409"])
def test_terms_outside_the_allowlist_are_refused_without_a_request(
    term: str,
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    def forbidden() -> StaffScheduleClient:
        raise AssertionError("no client may be built for a refused term")

    code = main(
        ["--terms", term, "--apply"], session_factory=session_factory, client_factory=forbidden
    )

    assert code == 2
    assert capsys.readouterr().out == ""
    assert count(session_factory, Section) == 0


def test_http_500_on_second_term_stops_with_nothing_written(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = graded_rows(session_factory)
    good = build_whole_term_html(rows, error_tail=False)

    def handler(request: httpx.Request) -> httpx.Response:
        term = parse_qs(request.content.decode(), keep_blank_values=True)["P_SEMESTER"][0]
        if term == "202501":
            return httpx.Response(500, text="boom", headers={"content-type": "text/html"})
        return httpx.Response(200, text=good, headers={"content-type": "text/html"})

    client, requests = usf_client(handler=handler)
    sleeps: list[float] = []

    code, report = run(
        ["--terms", "202408", "202501", "--apply"],
        session_factory,
        lambda: client,
        capsys,
        sleeps=sleeps,
    )

    assert code == 1
    assert len(requests) == 2
    assert report["status"] == "failed"
    assert report["failed_term"] == "202501"
    assert report["error_kind"] == "usf_http"
    assert report["written"] is False
    assert table_sizes(session_factory) == dict.fromkeys(
        ("Section", "SectionInstructor", "SeatSnapshot", "IngestRun", "SectionRankingCache"), 0
    )
    assert sleeps == [30.0]


def test_timeout_is_reported_as_a_coarse_kind(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    graded_rows(session_factory)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    client, requests = usf_client(handler=handler)
    code, report = run(["--terms", "202408", "--apply"], session_factory, lambda: client, capsys)

    assert code == 1
    assert len(requests) == 1
    assert report["error_kind"] == "usf_timeout"


def test_zero_parsed_rows_fail_the_guard_in_apply_and_dry_run(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    graded_rows(session_factory)
    client_factory, _ = client_for({"202408": []})

    for mode in ("--apply", "--dry-run"):
        code, report = run(["--terms", "202408", mode], session_factory, client_factory, capsys)
        assert code == 1
        assert "zero_rows" in term_of(report)["guard_failures"]
        assert count(session_factory, Section) == 0
        assert count(session_factory, IngestRun) == 0


def test_unmatched_grade_fraction_above_the_limit_writes_nothing(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = graded_rows(session_factory)
    add_grade(session_factory, term_id=2, crn="89035", course_id=10)
    client_factory, _ = client_for({"202408": rows})  # 89035 is missing: 1 of 3 unmatched

    code, report = run(["--terms", "202408", "--apply"], session_factory, client_factory, capsys)
    assert code == 1
    assert "unmatched_fraction" in term_of(report)["guard_failures"]
    assert term_of(report)["unmatched_grade_crns"] == 1
    assert count(session_factory, Section) == 0

    code, report = run(["--terms", "202408", "--dry-run"], session_factory, client_factory, capsys)
    assert code == 1
    assert count(session_factory, Section) == 0

    code, report = run(
        ["--terms", "202408", "--apply", "--max-unmatched-fraction", "0.5"],
        session_factory,
        client_factory,
        capsys,
    )
    assert code == 0
    assert count(session_factory, Section) == 2


def test_duplicate_crn_among_rows_to_write_aborts_before_any_write(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    add_grade(session_factory, term_id=2, crn="89033", course_id=10)
    rows = [
        RowSpec(crn="89033", subject="MAC", number="1105", section="001"),
        RowSpec(crn="89033", subject="MAC", number="1105", section="002"),
    ]
    client_factory, _ = client_for({"202408": rows})

    for mode in ("--apply", "--dry-run"):
        code, report = run(["--terms", "202408", mode], session_factory, client_factory, capsys)
        assert code == 1
        assert term_of(report)["guard_failures"] == ["duplicate_crn"]
        assert count(session_factory, Section) == 0

    selection = _selection(rows, {"89033": frozenset({("MAC", "1105")})}, {("MAC", "1105"): 10})
    with session_factory.begin() as session, pytest.raises(BackfillGuardError):
        write_term_backfill(session, term_id=2, selection=selection, observed_at=NOW)
    assert count(session_factory, Section) == 0


def test_non_tampa_unattributed_and_mismatched_rows_are_skipped_and_counted(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    add_grade(session_factory, term_id=2, crn="80001", course_id=10)
    add_grade(session_factory, term_id=2, crn="80002", course_id=None)
    add_grade(session_factory, term_id=2, crn="80003", course_id=11)
    add_grade(session_factory, term_id=2, crn="80004", course_id=10)
    rows = [
        RowSpec(crn="80001", subject="MAC", number="1105", campus="Online"),
        RowSpec(crn="80002", subject="MAC", number="1105"),
        RowSpec(crn="80003", subject="MAC", number="1105"),
        RowSpec(crn="80004", subject="MAC", number="1105"),
        RowSpec(crn="80009", subject="MAC", number="1105"),
    ]
    client_factory, _ = client_for({"202408": rows})

    code, report = run(["--terms", "202408", "--apply"], session_factory, client_factory, capsys)

    assert code == 0
    term = term_of(report)
    assert (
        term["fetched_rows"],
        term["not_graded"],
        term["non_tampa"],
        term["grade_course_unattributed"],
        term["course_key_mismatch"],
        term["to_write"],
    ) == (5, 1, 1, 1, 1, 1)
    with session_factory() as session:
        assert session.scalars(select(Section.crn)).all() == ["80004"]
        run_row = session.scalars(select(IngestRun)).one()
        assert (run_row.records_seen, run_row.records_inserted, run_row.records_failed) == (4, 1, 3)


def test_sleep_runs_between_terms_and_never_after_the_last(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = graded_rows(session_factory)
    client_factory, requests = client_for({"202408": rows, "202501": []})
    sleeps: list[float] = []

    run(
        ["--terms", "202408", "202501", "--dry-run", "--pause-seconds", "12"],
        session_factory,
        client_factory,
        capsys,
        sleeps=sleeps,
    )
    assert sleeps == [12.0]
    assert len(requests) == 2

    sleeps.clear()
    run(["--terms", "202408", "--dry-run"], session_factory, client_factory, capsys, sleeps=sleeps)
    assert sleeps == []


def test_pause_below_the_floor_is_rejected(session_factory: sessionmaker[Session]) -> None:
    code = main(
        ["--terms", "202408", "--apply", "--pause-seconds", "5"], session_factory=session_factory
    )
    assert code == 2


def test_batch_course_resolution_matches_resolve_course_id(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory.begin() as session:
        session.add_all(
            [
                Course(id=12, subject="MAC", number="1105", title="Old", catalog_edition="2024-25"),
                Course(id=13, subject="MAC", number="1105", title="New", catalog_edition="2027-28"),
            ]
        )
    with session_factory() as session:
        resolved = resolve_course_ids(session, [("MAC", "1105"), ("ENC", "1101"), ("ZZZ", "9999")])
        assert resolved == {
            ("MAC", "1105"): resolve_course_id(session, "MAC", "1105"),
            ("ENC", "1101"): resolve_course_id(session, "ENC", "1101"),
        }
        assert resolved[("MAC", "1105")] == 13


def _selection(
    specs: list[RowSpec],
    grade_keys: Mapping[str, frozenset[tuple[str, str] | None]],
    course_ids: Mapping[tuple[str, str], int],
) -> TermSelection:
    html = build_whole_term_html(specs, error_tail=False)
    return select_backfill_rows("202408", parse_whole_term(html).rows, grade_keys, course_ids)


def test_statements_do_not_grow_with_the_number_of_rows(
    engine: Engine,
    session_factory: sessionmaker[Session],
) -> None:
    def statements_for(count_rows: int, term_id: int, start_crn: int) -> int:
        specs = [
            RowSpec(
                crn=str(start_crn + i),
                subject="ENC",
                number="1101",
                section=f"{i + 1:03d}",
                instructor=f"Instructor {i}",
            )
            for i in range(count_rows)
        ]
        keys = {spec.crn: frozenset({("ENC", "1101")}) for spec in specs}
        selection = _selection(specs, keys, {("ENC", "1101"): 11})
        recorded: list[str] = []

        def record(conn: Any, cursor: Any, statement: str, *rest: Any) -> None:
            recorded.append(statement)

        event.listen(engine, "before_cursor_execute", record)
        try:
            with session_factory.begin() as session:
                write_term_backfill(session, term_id=term_id, selection=selection, observed_at=NOW)
        finally:
            event.remove(engine, "before_cursor_execute", record)
        return len(recorded)

    small = statements_for(10, term_id=2, start_crn=50000)
    large = statements_for(40, term_id=3, start_crn=60000)

    assert large == small
    assert count(session_factory, Section) == 50
    assert count(session_factory, SectionInstructor) == 50


def test_backfilled_history_survives_a_live_sweep_untouched(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = graded_rows(session_factory)
    client_factory, _ = client_for({"202408": rows})
    run(["--terms", "202408", "--apply"], session_factory, client_factory, capsys)

    def historical_state() -> list[tuple[object, ...]]:
        with session_factory() as session:
            return [
                (s.crn, s.removed_at, s.last_seen_at, s.first_seen_at, s.term_id)
                for s in session.scalars(select(Section).where(Section.term_id == 2))
            ]

    def historical_children() -> tuple[int, int]:
        with session_factory() as session:
            ids = select(Section.id).where(Section.term_id == 2)
            return (
                session.scalar(
                    select(func.count())
                    .select_from(SectionInstructor)
                    .where(SectionInstructor.section_id.in_(ids))
                )
                or 0,
                session.scalar(
                    select(func.count())
                    .select_from(SeatSnapshot)
                    .where(SeatSnapshot.section_id.in_(ids))
                )
                or 0,
            )

    before_state, before_children = historical_state(), historical_children()

    live_rows = enc_rows(12)
    seed_from_rows(session_factory, live_rows)
    outcome, _ = sweep_rows(session_factory, live_rows)

    assert outcome.status.value == "succeeded"
    assert historical_state() == before_state
    assert historical_children() == before_children == (2, 0)
    assert all(state[1] is None for state in historical_state())


def test_laboratory_sections_are_stored_and_listed_in_the_histogram(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    graded_rows(session_factory)
    rows = [
        RowSpec(crn="89033", subject="MAC", number="1105"),
        RowSpec(
            crn="89034",
            subject="ENC",
            number="1101",
            title="Composition I",
            section_type="Laboratory",
        ),
    ]
    client_factory, _ = client_for({"202408": rows})

    code, report = run(["--terms", "202408", "--apply"], session_factory, client_factory, capsys)

    assert code == 0
    assert term_of(report)["section_type_histogram"] == {"Class Lecture": 1, "Laboratory": 1}
    with session_factory() as session:
        stored = session.scalar(select(Section.section_type).where(Section.crn == "89034"))
        assert stored == "Laboratory"


def test_report_json_matches_stdout(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    rows = graded_rows(session_factory)
    client_factory, _ = client_for({"202408": rows})
    target = tmp_path / "report.json"

    _, report = run(
        ["--terms", "202408", "--dry-run", "--report-json", str(target)],
        session_factory,
        client_factory,
        capsys,
    )

    assert json.loads(target.read_text()) == report


def test_backfill_is_isolated_from_the_live_sync_and_the_worker() -> None:
    """D-05: no sync change-only/removal logic is imported, and the worker never runs this."""
    root = Path(__file__).resolve().parents[2]
    probe = (
        "import json, sys\n"
        "import easy_a.schedule.backfill_cli\n"
        "banned = ('easy_a.sync.apply', 'easy_a.sync.plan', 'easy_a.sync.sweep',"
        " 'easy_a.sync.cli', 'easy_a.sync.runner')\n"
        "print(json.dumps(sorted(name for name in banned if name in sys.modules)))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip().splitlines()[-1]) == []
    for name in ("render.yaml", "Dockerfile"):
        assert "backfill" not in (root / name).read_text().lower()
