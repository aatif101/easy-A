from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from easy_a.db import Base

spec = importlib.util.spec_from_file_location(
    "benchmark_rankings",
    Path(__file__).resolve().parents[2] / "scripts/benchmark_rankings_search.py",
)
benchmark = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = benchmark
spec.loader.exec_module(benchmark)


def test_report_uses_resolved_engine_and_redacts_credentials(capsys):
    engine = create_engine(
        "postgresql+psycopg://secret_user:secret_password@private.pooler.supabase.com:6543/postgres"
    )
    benchmark._report(durations=[0.1], dataset_size=3783, engine=engine, url=None)
    output = capsys.readouterr().out
    assert "Supabase" in output and "pooler=True" in output
    assert all(
        secret not in output for secret in ("secret_user", "secret_password", "private.pooler")
    )
    engine.dispose()


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://127.0.0.1.evil.test",
        "http://user:pass@localhost",
        "http://localhost/path",
        "http://localhost?x=1",
    ],
)
def test_http_target_rejects_non_loopback_or_ambiguous_urls(url):
    with pytest.raises(ValueError):
        benchmark._http_base_url(url)


def test_http_queries_validate_responses_and_use_same_mix():
    queries = benchmark._representative_queries(iterations=50, subjects=["MAC", "ENC"])
    seen = []

    def handler(request):
        seen.append(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "items": [],
                "total": 0,
                "limit": 50,
                "offset": int(request.url.params["offset"]),
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        for query in queries:
            benchmark._http_search(client, "http://127.0.0.1:8000", "202701", query)
    assert len(seen) == 50
    assert {p["sort"] for p in seen} == {s.value for s in benchmark.RankingSort}
    assert seen[0]["subject"] == "MAC"
    assert seen[0]["seats_open"] == "true"
    assert "subject" not in seen[1]
    for status, payload in [(500, {}), (200, {"items": []})]:
        with (
            httpx.Client(
                transport=httpx.MockTransport(
                    lambda request, status=status, payload=payload: httpx.Response(
                        status, json=payload
                    )
                )
            ) as client,
            pytest.raises(ValueError),
        ):
            benchmark._http_search(client, "http://127.0.0.1:8000", "202701", queries[0])


def test_live_mode_does_not_write_or_seed(monkeypatch, capsys):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        benchmark._seed_synthetic_dataset(
            session, term_code="202701", section_count=3, now=benchmark.datetime.now(benchmark.UTC)
        )
        benchmark.refresh_section_rankings(session, term="202701")
        session.commit()
    statements = []
    event.listen(
        engine,
        "before_cursor_execute",
        lambda conn, cursor, statement, parameters, context, executemany: statements.append(
            statement
        ),
    )
    monkeypatch.setattr(benchmark, "get_engine", lambda *args: engine)
    monkeypatch.setattr(
        benchmark, "_seed_synthetic_dataset", lambda *args, **kwargs: pytest.fail("live seed")
    )
    benchmark._run_live(term="202701", iterations=50, url=None, http_base_url=None)
    assert statements and all(
        s.lstrip().upper().startswith(("SELECT", "WITH"))
        and not re.search(r"\b(INSERT|UPDATE|DELETE)\b", s.upper())
        for s in statements
    )
    assert "stored term" in capsys.readouterr().out


def test_cli_rejects_unbounded_iterations_and_incompatible_modes():
    for args in (
        ["--live", "--iterations", "49"],
        ["--live", "--smoke"],
        ["--http-base-url", "http://127.0.0.1"],
        ["--iterations", "10001"],
    ):
        with pytest.raises(SystemExit):
            benchmark.main(args)


def test_live_failure_does_not_print_driver_secrets(monkeypatch, capsys):
    def fail(**kwargs):
        raise RuntimeError("postgres://secret_user:secret_password@private-host/db")

    monkeypatch.setattr(benchmark, "_run_live", fail)
    assert benchmark.main(["--live"]) == 1
    output = capsys.readouterr()
    assert "RuntimeError" in output.err
    assert "secret" not in output.err and "private-host" not in output.err


def test_live_mode_reconciles_active_sections_after_removal(monkeypatch, capsys):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        benchmark._seed_synthetic_dataset(
            session, term_code="202701", section_count=3, now=benchmark.datetime.now(benchmark.UTC)
        )
        # One section soft-removed by the sync worker; the cache is built from active only.
        removed = session.scalars(
            select(benchmark.Section).order_by(benchmark.Section.id).limit(1)
        ).one()
        removed.removed_at = benchmark.datetime.now(benchmark.UTC)
        session.flush()
        assert benchmark.refresh_section_rankings(session, term="202701") == 2
        session.commit()
    monkeypatch.setattr(benchmark, "get_engine", lambda *args: engine)
    benchmark._run_live(term="202701", iterations=50, url=None, http_base_url=None)
    assert "Dataset size: 2 sections (stored term)" in capsys.readouterr().out


@pytest.mark.parametrize(
    "value",
    ["https://easy-a-api.onrender.com", "https://easy-a-api.onrender.com/"],
)
def test_remote_origin_accepts_plain_https_origin(value):
    assert benchmark._remote_https_origin(value) == "https://easy-a-api.onrender.com"


@pytest.mark.parametrize(
    "value",
    [
        "http://easy-a-api.onrender.com",
        "https://user:pass@easy-a-api.onrender.com",
        "https://user@easy-a-api.onrender.com",
        "https://easy-a-api.onrender.com/api",
        "https://easy-a-api.onrender.com?x=1",
        "https://easy-a-api.onrender.com/?x=1",
        "https://easy-a-api.onrender.com#frag",
        "https://easy-a-api.onrender.com:notaport",
        "https://",
        "ftp://easy-a-api.onrender.com",
        "easy-a-api.onrender.com",
    ],
)
def test_remote_origin_rejects_non_plain_https_origins(value):
    with pytest.raises(ValueError, match="Remote target must be a plain https origin"):
        benchmark._remote_https_origin(value)


def test_loopback_validator_still_rejects_https_remote_origin():
    with pytest.raises(ValueError):
        benchmark._http_base_url("https://easy-a-api.onrender.com")


@pytest.mark.parametrize(
    "extra",
    [
        ["--live"],
        ["--smoke"],
        ["--url", "postgresql://u:p@h/db"],
        ["--http-base-url", "http://127.0.0.1:8000"],
        ["--iterations", "49"],
    ],
)
def test_cli_rejects_remote_url_combinations(extra, monkeypatch):
    monkeypatch.setattr(
        benchmark, "_run_remote", lambda **kwargs: pytest.fail("remote run must not start")
    )
    with pytest.raises(SystemExit):
        benchmark.main(["--remote-url", "https://easy-a-api.onrender.com", *extra])


def test_cli_rejects_invalid_remote_origin(monkeypatch):
    monkeypatch.setattr(
        benchmark, "_run_remote", lambda **kwargs: pytest.fail("remote run must not start")
    )
    with pytest.raises(SystemExit):
        benchmark.main(["--remote-url", "http://easy-a-api.onrender.com"])


def test_cli_dispatches_remote_run(monkeypatch):
    calls = []
    monkeypatch.setattr(benchmark, "_run_remote", lambda **kwargs: calls.append(kwargs))
    assert benchmark.main(["--remote-url", "https://easy-a-api.onrender.com/"]) == 0
    assert calls == [
        {"term": "202701", "iterations": 50, "base_url": "https://easy-a-api.onrender.com"}
    ]


def test_remote_run_reports_p95_and_sends_no_credentials(capsys):
    seen: list[httpx.Request] = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "items": [],
                "total": 3783,
                "limit": int(request.url.params["limit"]),
                "offset": int(request.url.params["offset"]),
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        benchmark._run_remote("202701", 50, "https://easy-a-api.onrender.com", client=client)
    output = capsys.readouterr().out
    # 1 broad precheck + 5 warmups + 50 timed calls.
    assert len(seen) == 56
    assert all(r.url.scheme == "https" and r.url.host == "easy-a-api.onrender.com" for r in seen)
    assert all("cookie" not in r.headers and "authorization" not in r.headers for r in seen)
    assert re.search(r"^p95: \d+\.\d\dms ", output, re.MULTILINE)
    assert re.search(r"^p50: ", output, re.MULTILINE) and re.search(r"^max: ", output, re.MULTILINE)
    assert "Iterations: 50" in output
    assert "no DB reconciliation" in output
    assert "Dataset size: 3783 sections (hosted API total)" in output


def test_remote_run_fails_on_empty_term_and_redirects():
    def empty(request):
        return httpx.Response(200, json={"items": [], "total": 0, "limit": 50, "offset": 0})

    with (
        httpx.Client(transport=httpx.MockTransport(empty)) as client,
        pytest.raises(ValueError),
    ):
        benchmark._run_remote("202701", 50, "https://easy-a-api.onrender.com", client=client)

    def redirect(request):
        return httpx.Response(302, headers={"location": "https://evil.example/"})

    with (
        httpx.Client(transport=httpx.MockTransport(redirect)) as client,
        pytest.raises(ValueError),
    ):
        benchmark._run_remote("202701", 50, "https://easy-a-api.onrender.com", client=client)


def test_remote_failure_does_not_print_transport_details(monkeypatch, capsys):
    def fail(**kwargs):
        raise RuntimeError("https://secret_user:secret_password@private-host/")

    monkeypatch.setattr(benchmark, "_run_remote", fail)
    assert benchmark.main(["--remote-url", "https://easy-a-api.onrender.com"]) == 1
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "secret" not in err and "private-host" not in err
