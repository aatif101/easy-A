"""D-05: courses USF lists but Easy-A lacks are auto-added, paced, capped and honestly labelled."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from easy_a.models import Course, IngestRun, SeatSnapshot, Section, SectionInstructor
from easy_a.rankings.cache import SectionRankingCache
from easy_a.sync.courses import CatalogSettings, CourseAdder
from easy_a.sync.runner import SweepStatus
from easy_a.sync.sweep import run_sweep
from tests.sync.sweep_support import (
    SWEEP_AT,
    TERM,
    enc_rows,
    seed_from_rows,
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
