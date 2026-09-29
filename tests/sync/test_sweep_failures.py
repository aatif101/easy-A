from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from easy_a.models import IngestRun
from easy_a.schema_guard import SchemaNotCurrentError
from easy_a.sync import SYNC_ERROR_KINDS, sync_source
from easy_a.sync import sweep as sweep_module
from easy_a.sync.runner import SweepStatus
from easy_a.sync.sweep import run_sweep, sanitize_error_detail
from tests.sync.sweep_support import (
    SWEEP_AT,
    TERM,
    enc_rows,
    section_marks,
    seed_from_rows,
    sweep_rows,
    table_counts,
    usf_client,
)
from tests.sync.wholeterm_html import RowSpec, build_whole_term_html


def _seed_rows() -> list[RowSpec]:
    return [
        RowSpec(crn="13173", instructor="J. Doe"),
        RowSpec(crn="19410", section="002", instructor="Staff"),
        *enc_rows(18),
    ]


def _assert_only_a_failed_run(
    session_factory: sessionmaker[Session],
    before_counts: dict[str, int],
    before_marks: dict[str, tuple[object, ...]],
    *,
    kind: str,
) -> IngestRun:
    after = table_counts(session_factory)
    assert after.pop("IngestRun") == before_counts["IngestRun"] + 1
    expected = dict(before_counts)
    expected.pop("IngestRun")
    assert after == expected
    assert section_marks(session_factory) == before_marks
    with session_factory() as session:
        run = session.scalar(select(IngestRun).order_by(IngestRun.id.desc()))
        assert run is not None
        assert run.source == sync_source(TERM)
        assert run.status == "failed"
        assert run.records_failed == 1
        assert run.error_message is not None
        assert run.error_message.startswith(f"{kind}: ")
        assert run.error_message.split(":", 1)[0] in SYNC_ERROR_KINDS
        assert "postgresql://" not in run.error_message
        assert "postgres://" not in run.error_message
        session.expunge(run)
        return run


def _timeout_handler(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("read timed out", request=request)


@pytest.mark.parametrize(
    ("kind", "build"),
    [
        ("usf_http", lambda: usf_client("", status_code=503)),
        ("usf_timeout", lambda: usf_client(handler=_timeout_handler)),
        ("usf_response", lambda: usf_client("{}", content_type="application/json")),
        (
            "parse",
            lambda: usf_client(build_whole_term_html(_seed_rows(), include_header=False)),
        ),
        (
            "parse",
            lambda: usf_client(
                build_whole_term_html(_seed_rows(), malformed_crns=["13173"]),
            ),
        ),
        (
            "scope",
            lambda: usf_client(
                build_whole_term_html([*_seed_rows(), RowSpec(crn="13173", section="009")])
            ),
        ),
        (
            "gate",
            lambda: usf_client(build_whole_term_html(_seed_rows()[3:])),
        ),
    ],
    ids=[
        "http-503",
        "timeout",
        "non-html",
        "missing-header",
        "short-row",
        "duplicate-crn",
        "gate-trip",
    ],
)
def test_every_failure_kind_leaves_the_database_unchanged_and_records_one_failed_run(
    session_factory: sessionmaker[Session],
    kind: str,
    build: Callable[[], tuple[object, list[httpx.Request]]],
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    before_counts = table_counts(session_factory)
    before_marks = section_marks(session_factory)
    client, requests = build()

    outcome = run_sweep(
        session_factory,
        term=TERM,
        client=client,  # type: ignore[arg-type]
        now_fn=lambda: SWEEP_AT,
    )

    assert len(requests) == 1
    assert outcome.status is SweepStatus.failed
    assert outcome.error_kind == kind
    _assert_only_a_failed_run(session_factory, before_counts, before_marks, kind=kind)


def test_gate_trip_reports_its_reasons(session_factory: sessionmaker[Session]) -> None:
    seed_from_rows(session_factory, _seed_rows())
    outcome, _ = sweep_rows(session_factory, _seed_rows()[3:])
    assert outcome.error_kind == "gate"
    assert any(reason.startswith("missing_fraction") for reason in outcome.gate_reasons)


def test_database_failure_after_partial_writes_rolls_everything_back(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    before_counts = table_counts(session_factory)
    before_marks = section_marks(session_factory)
    real_apply = sweep_module.apply_sweep_plan

    def apply_then_fail(*args: object, **kwargs: object) -> None:
        real_apply(*args, **kwargs)  # type: ignore[arg-type]
        raise OperationalError("INSERT", {}, Exception("connection dropped"))

    monkeypatch.setattr(sweep_module, "apply_sweep_plan", apply_then_fail)
    changed = [
        RowSpec(crn="13173", instructor="New Person"),
        RowSpec(crn="60000", section="050"),
        *_seed_rows()[1:],
    ]

    outcome, _ = sweep_rows(session_factory, changed)

    assert outcome.error_kind == "database"
    _assert_only_a_failed_run(session_factory, before_counts, before_marks, kind="database")


def test_schema_error_is_classified_as_schema(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_from_rows(session_factory, _seed_rows())

    def raise_schema(*args: object, **kwargs: object) -> None:
        raise SchemaNotCurrentError("migration 0004 not applied")

    monkeypatch.setattr(sweep_module, "load_db_state", raise_schema)
    outcome, _ = sweep_rows(session_factory, _seed_rows())
    assert outcome.error_kind == "schema"


def test_error_detail_never_carries_a_connection_url_and_is_capped(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    secret_url = "postgresql://postgres.abc:hunter2@aws-0.pooler.supabase.com:6543/postgres"

    def explode(*args: object, **kwargs: object) -> None:
        raise RuntimeError(f"boom {secret_url} " + "x" * 2000)

    monkeypatch.setattr(sweep_module, "load_db_state", explode)
    outcome, _ = sweep_rows(session_factory, _seed_rows())

    assert outcome.error_kind == "unexpected"
    with session_factory() as session:
        run = session.scalar(select(IngestRun).order_by(IngestRun.id.desc()))
        assert run is not None
        assert run.error_message is not None
        assert "hunter2" not in run.error_message
        assert "postgresql://" not in run.error_message
        assert run.error_message.startswith("unexpected: ")
        assert len(run.error_message) <= len("unexpected: ") + 500
    assert "hunter2" not in (outcome.error_detail or "")


def test_sanitizer_strips_urls_with_a_driver_suffix() -> None:
    cleaned = sanitize_error_detail("cannot reach postgresql+psycopg://u:p@h/db now")
    assert "psycopg" not in cleaned
    assert "u:p@h" not in cleaned


def test_busy_lock_makes_no_request_and_writes_nothing(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    before_counts = table_counts(session_factory)
    before_marks = section_marks(session_factory)
    monkeypatch.setattr(sweep_module, "try_sweep_lock", lambda session: False)
    client, requests = usf_client(build_whole_term_html(_seed_rows()))

    outcome = run_sweep(session_factory, term=TERM, client=client, now_fn=lambda: SWEEP_AT)

    assert outcome.status is SweepStatus.busy
    assert requests == []
    assert table_counts(session_factory) == before_counts
    assert section_marks(session_factory) == before_marks


def test_failure_to_record_the_failed_run_is_logged_not_raised(
    session_factory: sessionmaker[Session], caplog: pytest.LogCaptureFixture
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    client, _ = usf_client("", status_code=503)

    class BrokenFactory:
        """Delegates the first transaction, then fails the evidence transaction."""

        def __init__(self) -> None:
            self.opened = 0

        def begin(self) -> object:
            self.opened += 1
            if self.opened > 1:
                raise RuntimeError("database unavailable")
            return session_factory.begin()

    outcome = run_sweep(
        BrokenFactory(),  # type: ignore[arg-type]
        term=TERM,
        client=client,
        now_fn=lambda: SWEEP_AT,
    )

    assert outcome.status is SweepStatus.failed
    assert outcome.error_kind == "usf_http"
    assert "could not record the failed IngestRun" in caplog.text
