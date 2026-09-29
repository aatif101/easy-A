from __future__ import annotations

import json
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from easy_a.models import IngestRun
from easy_a.schedule.client import StaffScheduleClient
from easy_a.sync import sync_source
from easy_a.sync.cli import main
from tests.sync.sweep_support import (
    SWEEP_AT,
    TERM,
    Clock,
    enc_rows,
    seed_from_rows,
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
