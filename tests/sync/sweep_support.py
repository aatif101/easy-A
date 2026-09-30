"""Shared fixtures and helpers for the sweep tests (SQLite, MockTransport, synthetic HTML)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from easy_a.models import Course, IngestRun, SeatSnapshot, Section, SectionInstructor, Term
from easy_a.rankings.cache import SectionRankingCache, refresh_section_rankings
from easy_a.schedule.client import DEFAULT_USER_AGENT, StaffScheduleClient
from easy_a.schedule.ingest import ingest_schedule_html
from easy_a.sync.sweep import SweepOutcome, run_sweep
from tests.sync.wholeterm_html import RowSpec, build_whole_term_html

TERM = "202701"
SEED_AT = datetime(2026, 9, 29, 10, 0, tzinfo=UTC)
SWEEP_AT = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


class Clock:
    """A now_fn that returns SWEEP_AT, then one second later each call."""

    def __init__(self, start: datetime = SWEEP_AT) -> None:
        self.start = start
        self.calls = 0

    def __call__(self) -> datetime:
        value = self.start + timedelta(seconds=self.calls)
        self.calls += 1
        return value


def usf_client(
    html: str | Callable[[], httpx.Response] | None = None,
    *,
    status_code: int = 200,
    content_type: str = "text/html; charset=utf-8",
    handler: Callable[[httpx.Request], httpx.Response] | None = None,
) -> tuple[StaffScheduleClient, list[httpx.Request]]:
    """A StaffScheduleClient over a MockTransport; also returns the recorded requests."""
    requests: list[httpx.Request] = []

    def default_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            text=html if isinstance(html, str) else "",
            headers={"content-type": content_type},
        )

    active = handler or default_handler

    def recording(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return active(request)

    http = httpx.Client(
        base_url="https://usfweb.usf.edu",
        transport=httpx.MockTransport(recording),
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    return StaffScheduleClient(http), requests


def enc_rows(count: int = 10, *, start_crn: int = 30000, **overrides: object) -> list[RowSpec]:
    return [
        RowSpec(
            crn=str(start_crn + i),
            subject="ENC",
            number="1101",
            section=f"{i + 1:03d}",
            title="Composition I",
            **overrides,  # type: ignore[arg-type]
        )
        for i in range(count)
    ]


def seed_from_rows(
    session_factory: sessionmaker[Session],
    rows: Iterable[RowSpec],
    *,
    refresh_cache: bool = True,
) -> None:
    """Seed the database as a prior sync would have: one instructor row, one snapshot each."""
    html = build_whole_term_html(rows, error_tail=False)
    with session_factory.begin() as session:
        ingest_schedule_html(session, html, TERM, observed_at=SEED_AT)
        if refresh_cache:
            refresh_section_rankings(session, term=TERM)


def count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def table_counts(session_factory: sessionmaker[Session]) -> dict[str, int]:
    with session_factory() as session:
        return {
            model.__name__: count(session, model)
            for model in (
                Section,
                SectionInstructor,
                SeatSnapshot,
                SectionRankingCache,
                IngestRun,
                Term,
                Course,
            )
        }


def section_marks(session_factory: sessionmaker[Session]) -> dict[str, tuple[object, ...]]:
    with session_factory() as session:
        return {
            section.crn: (section.removed_at, section.last_seen_at, section.first_seen_at)
            for section in session.scalars(select(Section))
        }


def naive(value: datetime) -> datetime:
    """SQLite drops timezone metadata; PostgreSQL keeps UTC-aware values."""
    return value.replace(tzinfo=None)


def sweep_rows(
    session_factory: sessionmaker[Session],
    rows: Iterable[RowSpec],
    *,
    at: datetime = SWEEP_AT,
    dry_run: bool = False,
) -> tuple[SweepOutcome, list[httpx.Request]]:
    """Run one real (or dry) sweep against a MockTransport serving ``rows``."""
    client, requests = usf_client(build_whole_term_html(list(rows)))
    outcome = run_sweep(
        session_factory, term=TERM, client=client, now_fn=lambda: at, dry_run=dry_run
    )
    return outcome, requests
