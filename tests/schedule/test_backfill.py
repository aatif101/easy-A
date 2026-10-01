"""The one-off historical backfill, end to end over a fake USF client (SQLite, MockTransport)."""

from __future__ import annotations

import json
from collections.abc import Callable, Generator, Iterable
from datetime import UTC, datetime
from urllib.parse import parse_qs

import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.analytics.queries import get_instructor_course_historical_outcome_stats
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
from easy_a.schedule.backfill import BACKFILL_SOURCE, HISTORICAL_GRADE_TERMS
from easy_a.schedule.backfill_cli import main
from easy_a.schedule.client import StaffScheduleClient
from tests.sync.sweep_support import usf_client
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
) -> tuple[int, dict[str, object]]:
    recorded = sleeps if sleeps is not None else []
    code = main(
        argv,
        session_factory=session_factory,
        client_factory=client_factory,
        now_fn=lambda: NOW,
        sleep=recorded.append,
    )
    out = capsys.readouterr().out
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
