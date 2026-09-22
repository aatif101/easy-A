from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, event
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
    assert statements and all(s.lstrip().upper().startswith("SELECT") for s in statements)
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
