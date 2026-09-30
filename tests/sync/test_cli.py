from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from easy_a.db import Base
from easy_a.models import IngestRun, Section
from easy_a.rankings.cache import SectionRankingCache
from easy_a.schedule.client import StaffScheduleClient
from easy_a.sync import sync_source
from easy_a.sync.cli import build_parser, main
from tests.sync.sweep_support import (
    SWEEP_AT,
    TERM,
    Clock,
    enc_rows,
    section_marks,
    seed_from_rows,
    sweep_rows,
    table_counts,
    usf_client,
)
from tests.sync.wholeterm_html import RowSpec, build_whole_term_html

REPO_ROOT = Path(__file__).resolve().parents[2]


def _seed_rows() -> list[RowSpec]:
    return [
        RowSpec(crn="13173", instructor="Staff", enrollment=0, seats_remaining=135),
        RowSpec(crn="19410", section="002", instructor="Staff"),
        RowSpec(crn="20000", section="003", instructor="A. Smith"),
        *enc_rows(10),
    ]


def _response_rows() -> list[RowSpec]:
    return [
        RowSpec(crn="13173", instructor="J. Doe", enrollment=20, seats_remaining=115),
        RowSpec(crn="19410", section="002", instructor="Staff"),
        RowSpec(crn="21111", section="004", instructor="N. New"),
        RowSpec(crn="90001", subject="MAC", number="6000", section="001", title="Grad Algebra"),
        *enc_rows(10),
    ]


def _json_lines(output: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in output.splitlines() if line.startswith("{")]


def _factory(
    rows: list[RowSpec],
) -> tuple[list[httpx.Request], object]:
    client, requests = usf_client(build_whole_term_html(rows))

    def make() -> StaffScheduleClient:
        return client

    return requests, make


def test_once_runs_one_sweep_and_logs_one_json_line(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    requests, make = _factory(_response_rows())

    code = main(
        ["--term", TERM, "--once"],
        session_factory=session_factory,
        client_factory=make,  # type: ignore[arg-type]
        now_fn=Clock(),
    )

    out = capsys.readouterr().out
    assert code == 0
    assert len(requests) == 1
    lines = _json_lines(out)
    assert len(lines) == 1
    line = lines[0]
    assert line["event"] == "sweep_succeeded"
    assert line["term"] == TERM
    assert line["inserted"] == 1
    assert line["updated"] == 2
    assert line["removed"] == 1
    assert line["restored"] == 0
    assert line["instructor_changes"] == 1  # J. Doe appended on 13173; inserts carry their own
    assert line["seat_changes"] == 1  # 13173 seats changed; inserts carry their own snapshot
    assert line["scope"]["graduate_rows"] == 1  # type: ignore[index]
    assert line["scope"]["in_scope_rows"] == 13  # type: ignore[index]
    assert line["tail_error"] is True
    assert isinstance(line["bytes"], int) and line["bytes"] > 0
    assert line["gate_reasons"] == []
    assert line["error_kind"] is None
    assert isinstance(line["peak_rss_mb"], float)
    assert isinstance(line["duration_s"], float)
    assert isinstance(line["next_start_at"], str)
    with session_factory() as session:
        run = session.query(IngestRun).one()
        assert run.source == sync_source(TERM)
        assert run.status == "succeeded"


def test_second_once_is_refused_by_the_floor_with_an_iso_time(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    _, first = _factory(_response_rows())
    assert (
        main(
            ["--term", TERM, "--once"],
            session_factory=session_factory,
            client_factory=first,  # type: ignore[arg-type]
            now_fn=Clock(),
        )
        == 0
    )
    capsys.readouterr()

    requests, second = _factory(_response_rows())
    code = main(
        ["--term", TERM, "--once"],
        session_factory=session_factory,
        client_factory=second,  # type: ignore[arg-type]
        now_fn=Clock(),
    )

    out = capsys.readouterr().out
    assert code == 3
    assert requests == []
    assert "refused: next sweep allowed at " in out
    stamp = out.split("refused: next sweep allowed at ")[1].strip()
    assert stamp.startswith("2026-09-29T13:00") and stamp.endswith("+00:00")
    assert _json_lines(out) == []


def test_dry_run_reports_and_leaves_tables_unchanged(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    before = table_counts(session_factory)
    requests, make = _factory(_response_rows())

    code = main(
        ["--term", TERM, "--dry-run"],
        session_factory=session_factory,
        client_factory=make,  # type: ignore[arg-type]
        now_fn=Clock(),
    )

    lines = _json_lines(capsys.readouterr().out)
    assert code == 0
    assert len(requests) == 1
    assert [line["event"] for line in lines] == ["sweep_dry_run"]
    assert lines[0]["inserted"] == 1
    assert table_counts(session_factory) == before


def test_dry_run_is_also_refused_inside_the_floor(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    with session_factory.begin() as session:
        session.add(
            IngestRun(
                source=sync_source(TERM),
                status="failed",
                started_at=SWEEP_AT - timedelta(minutes=5),
                finished_at=SWEEP_AT - timedelta(minutes=4),
                error_message="usf_http: boom",
            )
        )
    requests, make = _factory(_response_rows())

    code = main(
        ["--term", TERM, "--dry-run"],
        session_factory=session_factory,
        client_factory=make,  # type: ignore[arg-type]
        now_fn=Clock(),
    )

    assert code == 3
    assert requests == []
    assert "refused: next sweep allowed at " in capsys.readouterr().out


def test_missing_removed_at_exits_4_naming_the_migration(
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE sections (id INTEGER PRIMARY KEY)"))
    requests, make = _factory([])

    code = main(
        ["--term", TERM, "--once"],
        session_factory=sessionmaker(bind=engine),
        client_factory=make,  # type: ignore[arg-type]
        now_fn=Clock(),
    )

    out = capsys.readouterr().out
    assert code == 4
    assert requests == []
    assert "0004_sync_removed_at" in out
    assert out.startswith("startup check failed:")
    engine.dispose()


def test_engine_failure_exits_4_without_leaking_the_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom() -> None:
        raise ValueError("cannot connect to postgresql://user:secret@db.example.com:5432/app")

    monkeypatch.setattr("easy_a.sync.cli.get_engine", boom)

    code = main(["--term", TERM, "--once"])

    captured = capsys.readouterr()
    assert code == 4
    assert "postgresql://" not in captured.out + captured.err
    assert "secret" not in captured.out + captured.err


def test_failed_sweep_exits_1_and_logs_no_connection_url(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_from_rows(session_factory, _seed_rows())

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "could not reach postgresql://user:secret@db.example.com:5432/app", request=request
        )

    client, requests = usf_client(handler=handler)

    code = main(
        ["--term", TERM, "--once"],
        session_factory=session_factory,
        client_factory=lambda: client,
        now_fn=Clock(),
    )

    captured = capsys.readouterr()
    lines = _json_lines(captured.out)
    assert code == 1
    assert len(requests) == 1
    assert [line["event"] for line in lines if str(line["event"]).startswith("sweep_")] == [
        "sweep_failed"
    ]
    failed = next(line for line in lines if line["event"] == "sweep_failed")
    assert failed["error_kind"] == "usf_http"
    assert "postgresql://" not in captured.out + captured.err
    assert "secret" not in captured.out + captured.err
    assert all(line.get("event") for line in lines)


def test_help_lists_every_option_in_a_subprocess() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "easy_a.sync", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    for option in (
        "--term",
        "--once",
        "--dry-run",
        "--restore-crn",
        "--log-level",
        "--max-missing-fraction",
    ):
        assert option in result.stdout


def test_once_and_dry_run_are_mutually_exclusive() -> None:
    assert main(["--term", TERM, "--once", "--dry-run"]) == 2


def test_invalid_term_is_a_usage_error() -> None:
    assert main(["--term", "2027", "--once"]) == 2


# -- loop mode ---------------------------------------------------------------------------------


def _stop_after_first_response(
    rows: list[RowSpec], stop: threading.Event
) -> tuple[list[httpx.Request], StaffScheduleClient]:
    html = build_whole_term_html(rows)

    def handler(request: httpx.Request) -> httpx.Response:
        threading.Timer(0.05, stop.set).start()
        return httpx.Response(200, text=html, headers={"content-type": "text/html; charset=utf-8"})

    client, requests = usf_client(handler=handler)
    return requests, client


def test_loop_sweeps_once_then_stops_cleanly_on_the_stop_event(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    stop = threading.Event()
    watchdog = threading.Timer(20, stop.set)
    watchdog.start()
    requests, client = _stop_after_first_response(_response_rows(), stop)

    try:
        code = main(
            ["--term", TERM],
            session_factory=session_factory,
            client_factory=lambda: client,
            now_fn=lambda: SWEEP_AT,
            stop_event=stop,
        )
    finally:
        watchdog.cancel()

    events = [line["event"] for line in _json_lines(capsys.readouterr().out)]
    assert code == 0
    assert len(requests) == 1
    assert events.count("sweep_succeeded") == 1
    assert events[-1] == "worker_stopped"
    assert "sleeping" in events


def test_loop_restart_with_a_recent_ingest_run_waits_instead_of_sweeping(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    with session_factory.begin() as session:
        session.add(
            IngestRun(
                source=sync_source(TERM),
                status="succeeded",
                started_at=SWEEP_AT - timedelta(minutes=10),
                finished_at=SWEEP_AT - timedelta(minutes=9),
            )
        )
    stop = threading.Event()
    threading.Timer(0.2, stop.set).start()
    requests, make = _factory(_response_rows())

    code = main(
        ["--term", TERM],
        session_factory=session_factory,
        client_factory=make,  # type: ignore[arg-type]
        now_fn=lambda: SWEEP_AT,
        stop_event=stop,
    )

    events = [line["event"] for line in _json_lines(capsys.readouterr().out)]
    assert code == 0
    assert requests == []
    assert "sleeping" in events
    assert not any(str(event).startswith("sweep_") for event in events)
    assert events[-1] == "worker_stopped"


def test_sigterm_stops_a_sleeping_worker_process_with_exit_0(tmp_path: Path) -> None:
    """Real process, real signal handlers, SQLite file database (never the hosted database)."""
    import signal
    import time

    db_path = tmp_path / "worker.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            IngestRun(
                source=sync_source(TERM),
                status="succeeded",
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
            )
        )
        session.commit()
    engine.dispose()

    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite+pysqlite:///{db_path}",
        "EASY_A_REGISTRATION_WINDOWS_PATH": str(REPO_ROOT / "config" / "registration_windows.toml"),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "easy_a.sync", "--term", TERM],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    watchdog = threading.Timer(60, proc.kill)
    watchdog.start()
    try:
        assert proc.stdout is not None
        seen: list[str] = []
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            seen.append(line)
            if '"event": "sleeping"' in line:
                break
        assert any('"sleeping"' in line for line in seen), (seen, proc.stderr.read())  # type: ignore[union-attr]
        started = time.monotonic()
        proc.send_signal(signal.SIGTERM)
        remaining = proc.stdout.read()
        code = proc.wait(timeout=15)
        elapsed = time.monotonic() - started
    finally:
        watchdog.cancel()
        if proc.poll() is None:
            proc.kill()
    assert code == 0
    assert elapsed < 5
    assert '"event": "worker_stopped"' in remaining


# -- restore mode ------------------------------------------------------------------------------


def _forbidden_client() -> StaffScheduleClient:
    raise AssertionError("--restore-crn must not create a USF client")


def test_restore_crn_clears_removed_at_and_restores_the_cache_row_without_http(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    # A real sweep whose response omits 20000 marks it removed and drops its cache row.
    rows = [row for row in _response_rows() if row.crn != "90001"]
    sweep_rows(session_factory, rows)
    with session_factory() as session:
        removed = session.scalar(select(Section.removed_at).where(Section.crn == "20000"))
        assert removed is not None
        assert "20000" not in set(session.scalars(select(SectionRankingCache.crn)))

    code = main(
        [
            "--term",
            TERM,
            "--restore-crn",
            "20000",
            "--restore-crn",
            "13173",
            "--restore-crn",
            "99999",
        ],
        session_factory=session_factory,
        client_factory=_forbidden_client,
        now_fn=Clock(),
    )

    lines = _json_lines(capsys.readouterr().out)
    assert code == 0
    assert len(lines) == 1
    assert lines[0]["event"] == "restored"
    assert lines[0]["crns"] == ["20000"]
    assert lines[0]["not_found"] == ["99999"]
    assert lines[0]["not_removed"] == ["13173"]
    with session_factory() as session:
        assert session.scalar(select(Section.removed_at).where(Section.crn == "20000")) is None
        assert "20000" in set(session.scalars(select(SectionRankingCache.crn)))


def test_restore_crn_with_nothing_restorable_exits_1(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    before = table_counts(session_factory)

    code = main(
        ["--term", TERM, "--restore-crn", "13173"],
        session_factory=session_factory,
        client_factory=_forbidden_client,
        now_fn=Clock(),
    )

    assert code == 1
    assert _json_lines(capsys.readouterr().out)[0]["not_removed"] == ["13173"]
    assert table_counts(session_factory) == before


def test_restore_crn_rejects_a_malformed_crn() -> None:
    assert main(["--term", TERM, "--restore-crn", "123"]) == 2


# -- option validation -------------------------------------------------------------------------


@pytest.mark.parametrize("extra", [[], ["--restore-crn", "20000"]])
def test_max_missing_fraction_requires_once_or_dry_run(extra: list[str]) -> None:
    assert main(["--term", TERM, "--max-missing-fraction", "0.5", *extra]) == 2


def _mass_removal_rows() -> list[RowSpec]:
    """Only 8 of the 13 seeded sections come back: 38% missing, far above the default 10%."""
    return enc_rows(8)


def test_default_gate_refuses_a_mass_removal_in_dry_run(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    _, make = _factory(_mass_removal_rows())

    code = main(
        ["--term", TERM, "--dry-run"],
        session_factory=session_factory,
        client_factory=make,  # type: ignore[arg-type]
        now_fn=Clock(),
    )

    failed = next(
        line for line in _json_lines(capsys.readouterr().out) if line["event"] == "sweep_failed"
    )
    assert code == 1
    assert failed["error_kind"] == "gate"
    assert failed["gate_reasons"]


@pytest.mark.parametrize("mode", ["--once", "--dry-run"])
def test_max_missing_fraction_override_lets_the_operator_apply_a_mass_removal(
    mode: str, session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    _, make = _factory(_mass_removal_rows())

    code = main(
        ["--term", TERM, mode, "--max-missing-fraction", "0.9"],
        session_factory=session_factory,
        client_factory=make,  # type: ignore[arg-type]
        now_fn=Clock(),
    )

    lines = [
        line
        for line in _json_lines(capsys.readouterr().out)
        if str(line["event"]).startswith("sweep_")
    ]
    assert code == 0
    assert [line["event"] for line in lines] == [
        "sweep_succeeded" if mode == "--once" else "sweep_dry_run"
    ]
    assert lines[0]["removed"] == 5


def _seed_prior_success(session_factory: sessionmaker[Session], *, records_seen: int = 13) -> None:
    """A succeeded sweep two hours before SWEEP_AT: outside the 60 minute floor on this date."""
    started = SWEEP_AT - timedelta(hours=2)
    with session_factory.begin() as session:
        session.add(
            IngestRun(
                source=sync_source(TERM),
                status="succeeded",
                started_at=started,
                finished_at=started + timedelta(seconds=40),
                records_seen=records_seen,
            )
        )


@pytest.mark.parametrize("mode", ["--once", "--dry-run"])
def test_override_applies_a_mass_removal_after_a_prior_succeeded_sweep(
    mode: str, session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    _seed_prior_success(session_factory)
    before = table_counts(session_factory)
    _, make = _factory(_mass_removal_rows())

    code = main(
        ["--term", TERM, mode, "--max-missing-fraction", "0.9"],
        session_factory=session_factory,
        client_factory=make,  # type: ignore[arg-type]
        now_fn=Clock(),
    )

    lines = [
        line
        for line in _json_lines(capsys.readouterr().out)
        if str(line["event"]).startswith("sweep_")
    ]
    assert code == 0
    assert [line["event"] for line in lines] == [
        "sweep_succeeded" if mode == "--once" else "sweep_dry_run"
    ]
    assert lines[0]["removed"] == 5
    assert lines[0]["gate_reasons"] == []
    if mode == "--once":
        with session_factory() as session:
            newest = session.scalars(select(IngestRun).order_by(IngestRun.id.desc())).first()
            assert newest is not None
            assert newest.status == "succeeded"
            assert newest.records_seen == 8
    else:
        assert table_counts(session_factory) == before


def test_default_gate_refuses_a_mass_removal_after_a_prior_succeeded_sweep(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    _seed_prior_success(session_factory)
    marks_before = section_marks(session_factory)
    counts_before = table_counts(session_factory)
    _, make = _factory(_mass_removal_rows())

    code = main(
        ["--term", TERM, "--once"],
        session_factory=session_factory,
        client_factory=make,  # type: ignore[arg-type]
        now_fn=Clock(),
    )

    lines = [
        line
        for line in _json_lines(capsys.readouterr().out)
        if str(line["event"]).startswith("sweep_")
    ]
    assert code == 1
    assert [line["event"] for line in lines] == ["sweep_failed"]
    assert lines[0]["error_kind"] == "gate"
    reasons = lines[0]["gate_reasons"]
    assert isinstance(reasons, list) and len(reasons) == 2
    assert str(reasons[0]).startswith("missing_fraction")
    assert reasons[1] == "row_floor 8 below 90% of 13"
    assert section_marks(session_factory) == marks_before
    assert all(marks[0] is None for marks in section_marks(session_factory).values())
    counts_after = table_counts(session_factory)
    assert counts_after == {**counts_before, "IngestRun": counts_before["IngestRun"] + 1}
    with session_factory() as session:
        newest = session.scalars(select(IngestRun).order_by(IngestRun.id.desc())).first()
        assert newest is not None
        assert newest.status == "failed"
        assert (newest.error_message or "").startswith("gate:")


def test_next_default_sweep_passes_after_an_override_sweep(
    session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    _seed_prior_success(session_factory)
    _, first = _factory(_mass_removal_rows())
    assert (
        main(
            ["--term", TERM, "--once", "--max-missing-fraction", "0.9"],
            session_factory=session_factory,
            client_factory=first,  # type: ignore[arg-type]
            now_fn=Clock(),
        )
        == 0
    )
    capsys.readouterr()

    _, second = _factory(_mass_removal_rows())
    code = main(
        ["--term", TERM, "--once"],
        session_factory=session_factory,
        client_factory=second,  # type: ignore[arg-type]
        now_fn=Clock(start=SWEEP_AT + timedelta(hours=2)),
    )

    lines = [
        line
        for line in _json_lines(capsys.readouterr().out)
        if str(line["event"]).startswith("sweep_")
    ]
    assert code == 0
    assert [line["event"] for line in lines] == ["sweep_succeeded"]
    assert lines[0]["removed"] == 0
    assert lines[0]["gate_reasons"] == []


def test_help_describes_what_the_gate_override_relaxes() -> None:
    text = " ".join(build_parser().format_help().split())

    assert "row floor" in text
    assert "absent subject" in text
    assert "empty response" in text
