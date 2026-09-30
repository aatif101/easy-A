"""D-05: courses USF lists but Easy-A lacks are auto-added, paced, capped and honestly labelled."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from easy_a.models import Course, IngestRun, SeatSnapshot, Section, SectionInstructor
from easy_a.rankings.cache import SectionRankingCache
from easy_a.sync import courses as courses_module
from easy_a.sync.courses import (
    CatalogSettings,
    CatalogSettingsError,
    CourseAdder,
    default_course_adder,
    load_catalog_settings,
)
from easy_a.sync.runner import SweepStatus
from easy_a.sync.sweep import SweepOutcome, run_sweep
from tests.sync.sweep_support import (
    SWEEP_AT,
    TERM,
    enc_rows,
    seed_from_rows,
    table_counts,
    usf_client,
)
from tests.sync.wholeterm_html import RowSpec, build_whole_term_html

EDITION = "2026-2027"
TEMPLATE = "https://catalog.example/prefix/{subject}/code/{number}"
SETTINGS = CatalogSettings(catalog_edition=EDITION, catalog_url_template=TEMPLATE)


def catalog_page(subject: str, number: str, title: str = "Leadership Studies") -> str:
    """The shape of a live cloud.usf.edu course page (heading plus credit hours)."""
    return (
        "<html><body>"
        f"<h1>{subject} {number}: {title}</h1>"
        "<table><tr><th>Credit Hours:</th><td>3</td></tr></table>"
        "</body></html>"
    )


class FakeCatalog:
    """A recording fetch that serves a catalog page for every requested course."""

    def __init__(self) -> None:
        self.urls: list[str] = []

    def __call__(self, url: str) -> str:
        self.urls.append(url)
        subject, number = url.rstrip("/").split("/")[-3], url.rstrip("/").split("/")[-1]
        return catalog_page(subject, number)


def make_adder(fetch: FakeCatalog) -> CourseAdder:
    return CourseAdder(fetch=fetch, sleep=lambda seconds: None, settings=SETTINGS)


def _seed_rows() -> list[RowSpec]:
    return [RowSpec(crn="13173", instructor="Staff"), *enc_rows(9)]


def test_unknown_course_is_added_in_the_same_sweep_with_the_honest_fallback_label(
    session_factory: sessionmaker[Session],
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    ldr = [
        RowSpec(
            crn="41001",
            subject="LDR",
            number="3363",
            section="001",
            title="Leadership Studies",
            instructor="Kim",
        ),
        RowSpec(
            crn="41002",
            subject="LDR",
            number="3363",
            section="002",
            title="Leadership Studies",
            instructor="Lee",
        ),
    ]
    catalog = FakeCatalog()
    client, requests = usf_client(build_whole_term_html([*_seed_rows(), *ldr]))

    outcome = run_sweep(
        session_factory,
        term=TERM,
        client=client,
        now_fn=lambda: SWEEP_AT,
        course_adder=make_adder(catalog),
    )

    assert len(requests) == 1
    assert outcome.status is SweepStatus.succeeded
    assert outcome.auto_added == ("LDR 3363",)
    assert outcome.unapplied == ()
    assert outcome.unknown_course_keys == ()
    assert outcome.counts is not None
    assert outcome.counts.records_inserted == 2
    assert outcome.counts.records_failed == 0
    assert catalog.urls == ["https://catalog.example/prefix/LDR/code/3363"]

    with session_factory() as session:
        course = session.scalar(select(Course).where(Course.subject == "LDR"))
        assert course is not None
        assert (course.number, course.catalog_edition) == ("3363", EDITION)
        sections = list(session.scalars(select(Section).where(Section.course_id == course.id)))
        assert sorted(section.crn for section in sections) == ["41001", "41002"]
        for section in sections:
            instructors = list(
                session.scalars(
                    select(SectionInstructor).where(SectionInstructor.section_id == section.id)
                )
            )
            snapshots = list(
                session.scalars(select(SeatSnapshot).where(SeatSnapshot.section_id == section.id))
            )
            assert len(instructors) == 1
            assert len(snapshots) == 1

        cached = list(
            session.scalars(select(SectionRankingCache).where(SectionRankingCache.subject == "LDR"))
        )
        assert sorted(row.crn for row in cached) == ["41001", "41002"]
        for row in cached:
            assert row.score_source in {"subject", "global"}
            assert row.effective_n == 0

        run = session.scalar(select(IngestRun).order_by(IngestRun.id.desc()))
        assert run is not None
        assert run.status == "succeeded"
        assert run.records_failed == 0
        assert run.error_message is None


class Clock:
    """A mutable clock the adder reads, so tests can move time between sweeps."""

    def __init__(self, start: datetime = SWEEP_AT) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now


class Sleeps:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def ldr_rows(numbers: list[str], *, start_crn: int = 41000) -> list[RowSpec]:
    """One in-scope section per course number, subject LDR."""
    return [
        RowSpec(
            crn=str(start_crn + index),
            subject="LDR",
            number=number,
            section="001",
            title="Leadership Studies",
            instructor="Kim",
        )
        for index, number in enumerate(numbers)
    ]


def sweep_with(
    session_factory: sessionmaker[Session],
    rows: list[RowSpec],
    adder: CourseAdder | None,
    *,
    at: datetime = SWEEP_AT,
    dry_run: bool = False,
) -> tuple[SweepOutcome, list[httpx.Request]]:
    client, requests = usf_client(build_whole_term_html(rows))
    outcome = run_sweep(
        session_factory,
        term=TERM,
        client=client,
        now_fn=lambda: at,
        dry_run=dry_run,
        course_adder=adder,
    )
    return outcome, requests


def test_requests_are_paced_two_seconds_apart_with_no_initial_delay(
    session_factory: sessionmaker[Session],
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    sleeps = Sleeps()
    catalog = FakeCatalog()
    adder = CourseAdder(fetch=catalog, sleep=sleeps, settings=SETTINGS)
    graduate = RowSpec(crn="90001", subject="MAC", number="6000", title="Grad Algebra")
    rows = [*_seed_rows(), *ldr_rows(["3301", "3302", "3303"]), graduate]

    outcome, _ = sweep_with(session_factory, rows, adder)

    assert outcome.auto_added == ("LDR 3301", "LDR 3302", "LDR 3303")
    assert sleeps.calls == [2.0, 2.0]
    # Only the in-scope unknown courses are requested: never the graduate course, no crawling.
    assert [url.rsplit("/", 1)[-1] for url in catalog.urls] == ["3301", "3302", "3303"]


def test_per_sweep_cap_defers_the_eleventh_course_to_a_later_sweep(
    session_factory: sessionmaker[Session],
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    clock = Clock()
    catalog = FakeCatalog()
    adder = CourseAdder(fetch=catalog, sleep=lambda seconds: None, now_fn=clock, settings=SETTINGS)
    numbers = [f"33{index:02d}" for index in range(1, 12)]
    rows = [*_seed_rows(), *ldr_rows(numbers)]

    first, _ = sweep_with(session_factory, rows, adder)

    assert first.status is SweepStatus.succeeded
    assert len(catalog.urls) == 10
    assert first.unapplied == ("LDR 3311 (deferred: per-sweep cap)",)
    assert first.unknown_course_keys == ("LDR 3311",)
    assert first.counts is not None
    assert first.counts.records_failed == 1
    assert first.counts.records_inserted == 10
    with session_factory() as session:
        run = session.scalar(select(IngestRun).order_by(IngestRun.id.desc()))
        assert run is not None
        assert run.records_failed == 1
        assert run.error_message == "unapplied courses: LDR 3311 (deferred: per-sweep cap)"

    clock.now = SWEEP_AT + timedelta(hours=1)
    second, _ = sweep_with(session_factory, rows, adder, at=clock.now)

    assert second.status is SweepStatus.succeeded
    assert second.auto_added == ("LDR 3311",)
    assert len(catalog.urls) == 11
    assert catalog.urls[-1].endswith("/LDR/code/3311")
    assert second.counts is not None
    assert second.counts.records_failed == 0
    assert second.counts.records_inserted == 1


def test_failed_courses_are_named_and_the_sweep_still_succeeds(
    session_factory: sessionmaker[Session],
) -> None:
    seed_from_rows(session_factory, _seed_rows())

    def fetch(url: str) -> str:
        number = url.rsplit("/", 1)[-1]
        if number == "3301":
            raise httpx.ConnectError("boom")
        if number == "3302":
            return "<html><body><p>Page not found</p></body></html>"
        if number == "3303":
            return catalog_page("LDR", "9999")
        return catalog_page("LDR", number)

    adder = CourseAdder(fetch=fetch, sleep=lambda seconds: None, settings=SETTINGS)
    rows = [*_seed_rows(), *ldr_rows(["3301", "3302", "3303", "3304"])]

    outcome, _ = sweep_with(session_factory, rows, adder)

    assert outcome.status is SweepStatus.succeeded
    assert outcome.auto_added == ("LDR 3304",)
    assert outcome.unapplied == (
        "LDR 3301 (fetch failed: ConnectError)",
        "LDR 3302 (no catalog heading)",
        "LDR 3303 (catalog page did not describe LDR 3303)",
    )
    assert outcome.counts is not None
    assert outcome.counts.records_failed == 3
    assert outcome.counts.records_inserted == 1
    with session_factory() as session:
        run = session.scalar(select(IngestRun).order_by(IngestRun.id.desc()))
        assert run is not None
        assert run.status == "succeeded"
        assert run.records_failed == 3
        assert run.error_message == "unapplied courses: " + "; ".join(outcome.unapplied)
        assert session.scalar(select(Course).where(Course.number == "3301")) is None
        assert session.scalar(select(Course).where(Course.number == "3304")) is not None


def test_failed_course_is_negative_cached_for_six_hours(
    session_factory: sessionmaker[Session],
) -> None:
    clock = Clock()
    urls: list[str] = []

    def fetch(url: str) -> str:
        urls.append(url)
        raise httpx.ConnectError("boom")

    adder = CourseAdder(fetch=fetch, sleep=lambda seconds: None, now_fn=clock, settings=SETTINGS)
    key = ("LDR", "3301")

    with session_factory() as session:
        first = adder.add_missing(session, [key])
        assert first.failed == ((key, "fetch failed: ConnectError"),)
        assert len(urls) == 1

        clock.now = SWEEP_AT + timedelta(hours=1)
        cached = adder.add_missing(session, [key])
        assert len(urls) == 1
        assert cached.failed[0][0] == key
        expected_until = (SWEEP_AT + timedelta(hours=6)).isoformat()
        assert cached.failed[0][1] == f"negative-cached until {expected_until}"

        clock.now = SWEEP_AT + timedelta(hours=6, minutes=1)
        adder.add_missing(session, [key])
        assert len(urls) == 2


def test_dry_run_never_fetches_and_lists_the_would_add_keys(
    session_factory: sessionmaker[Session],
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    counts_before = table_counts(session_factory)
    catalog = FakeCatalog()
    rows = [*_seed_rows(), *ldr_rows(["3301", "3302"])]

    outcome, _ = sweep_with(session_factory, rows, make_adder(catalog), dry_run=True)

    assert outcome.status is SweepStatus.dry_run
    assert catalog.urls == []
    assert outcome.would_add == ("LDR 3301", "LDR 3302")
    assert outcome.auto_added == ()
    assert table_counts(session_factory) == counts_before


def test_default_adder_singleton_is_reused_across_sweeps(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    urls: list[str] = []

    def fetch(url: str) -> str:
        urls.append(url)
        raise httpx.ConnectError("boom")

    courses_module.reset_default_course_adder()
    monkeypatch.setattr(courses_module, "fetch_catalog_html", fetch)
    monkeypatch.setattr(courses_module, "load_catalog_settings", lambda: SETTINGS)
    try:
        assert default_course_adder() is default_course_adder()
        rows = [*_seed_rows(), *ldr_rows(["3301"])]

        first, _ = sweep_with(session_factory, rows, None)
        second, _ = sweep_with(session_factory, rows, None)
    finally:
        courses_module.reset_default_course_adder()

    assert first.unapplied == ("LDR 3301 (fetch failed: ConnectError)",)
    assert second.status is SweepStatus.succeeded
    assert second.unapplied[0].startswith("LDR 3301 (negative-cached until ")
    assert len(urls) == 1


def test_catalog_settings_without_a_template_raise_a_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "targets.toml"
    path.write_text('catalog_edition = "2026-2027"\n', encoding="utf-8")
    with pytest.raises(CatalogSettingsError, match="catalog_url_template"):
        load_catalog_settings(path)

    path.write_text(
        'catalog_edition = "2026-2027"\ncatalog_url_template = "https://x/{subject}"\n',
        encoding="utf-8",
    )
    with pytest.raises(CatalogSettingsError, match=r"\{subject\} and \{number\}"):
        load_catalog_settings(path)

    path.write_text(
        'catalog_edition = "2026-2027"\ncatalog_url_template = "https://x/{subject}/{number}"\n',
        encoding="utf-8",
    )
    assert load_catalog_settings(path) == CatalogSettings(
        "2026-2027", "https://x/{subject}/{number}"
    )


def test_bad_catalog_settings_fail_the_sweep_with_no_partial_writes(
    session_factory: sessionmaker[Session], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    path = tmp_path / "targets.toml"
    path.write_text('catalog_edition = "2026-2027"\n', encoding="utf-8")
    monkeypatch.setattr(
        courses_module, "get_settings", lambda: SimpleNamespace(course_targets_path=str(path))
    )
    before = table_counts(session_factory)
    catalog = FakeCatalog()
    adder = CourseAdder(fetch=catalog, sleep=lambda seconds: None)
    rows = [*_seed_rows(), *ldr_rows(["3301"])]

    outcome, _ = sweep_with(session_factory, rows, adder)

    assert outcome.status is SweepStatus.failed
    assert outcome.error_kind == "unexpected"
    assert catalog.urls == []
    after = table_counts(session_factory)
    assert after.pop("IngestRun") == before.pop("IngestRun") + 1
    assert after == before
