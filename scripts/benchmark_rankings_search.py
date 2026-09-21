"""Benchmark GET /api/v1/rankings/search over a seeded synthetic dataset.

This is a repeatable, offline-capable performance harness for REQ-PERF-01. It seeds a
parameterized number of synthetic sections -- clearly labeled a test fixture -- and times
representative rankings-search queries against the rewritten cache-backed search path
(Phase 03.5 Plan 02), printing p50/p95/max latency with the dataset size and environment on
every reported number.

Two run modes:
- ``--smoke``: seeds a small dataset on in-memory SQLite. No network, no credentials, safe to
  run in CI as a self-verification of the harness itself.
- default: seeds the requested dataset inside a throwaway PostgreSQL schema on a real
  PostgreSQL/Supabase instance (``--url``, else the ``DATABASE_URL`` environment variable via
  ``easy_a.db``). The schema and every row created inside it are rolled back at the end of the
  run and are never committed -- this harness never writes synthetic rows into the real
  coverage database (D-04).

The connection string / credentials are never printed or logged. Only the SQL dialect name and
a transaction-pooler boolean are reported.
"""

from __future__ import annotations

import argparse
import math
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from easy_a.api.routes.rankings import search_rankings
from easy_a.api.schemas import RankingSort
from easy_a.common.terms import TermParseError, normalize_banner_term_code
from easy_a.db import Base, get_engine, is_transaction_pooler
from easy_a.models import Course, GradeDistribution, SeatSnapshot, Section, SectionInstructor, Term
from easy_a.rankings.cache import refresh_section_rankings

DEFAULT_TERM = "202701"
DEFAULT_ITERATIONS = 50
DEFAULT_SECTIONS = 3782
SECTIONS_PER_COURSE = 15
SUBJECTS: tuple[str, ...] = (
    "MAC",
    "ENC",
    "AMH",
    "PSY",
    "BSC",
    "CHM",
    "PHY",
    "STA",
    "ECO",
    "POS",
    "SPC",
    "ENG",
    "HIS",
    "ANT",
    "SOC",
    "ART",
    "MUS",
    "PHI",
    "REL",
    "CGS",
    "COP",
    "ISM",
    "FIN",
    "MAN",
)
_SUFFIX_TO_SEASON = {"01": "Spring", "05": "Summer", "08": "Fall"}


@dataclass(frozen=True)
class _SearchQuery:
    subject: str | None
    seats_open: bool
    min_easiness: float | None
    sort: RankingSort
    limit: int
    offset: int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark GET /api/v1/rankings/search over a seeded synthetic test fixture. "
            "Never writes to the real coverage database."
        )
    )
    parser.add_argument(
        "--term",
        type=_term_code,
        default=DEFAULT_TERM,
        help=f"Banner term code for the seeded fixture. Default: {DEFAULT_TERM}.",
    )
    parser.add_argument(
        "--iterations",
        type=_positive_int,
        default=DEFAULT_ITERATIONS,
        help=f"Number of representative search calls to time. Default: {DEFAULT_ITERATIONS}.",
    )
    parser.add_argument(
        "--sections",
        type=_positive_int,
        default=DEFAULT_SECTIONS,
        help=f"Number of synthetic sections to seed. Default: {DEFAULT_SECTIONS}.",
    )
    parser.add_argument(
        "--url",
        default=None,
        help=(
            "Optional PostgreSQL/Supabase connection URL. If omitted, the DATABASE_URL "
            "environment variable is used via easy_a.db. Never printed or logged."
        ),
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help=(
            "Run a small, CI-safe pass on in-memory SQLite. Ignores --url and DATABASE_URL; "
            "no network access."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.smoke:
        _run_smoke(term=args.term, iterations=args.iterations, sections=args.sections)
        return 0
    _run_against_postgres(
        term=args.term,
        iterations=args.iterations,
        sections=args.sections,
        url=args.url,
    )
    return 0


def _run_smoke(*, term: str, iterations: int, sections: int) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            _seed_and_measure(
                session,
                engine=engine,
                url=None,
                term=term,
                iterations=iterations,
                sections=sections,
            )
    finally:
        engine.dispose()


def _run_against_postgres(
    *, term: str, iterations: int, sections: int, url: str | None
) -> None:
    engine = get_engine(url) if url else get_engine()
    try:
        if engine.dialect.name != "postgresql":
            raise RuntimeError(
                "Benchmark requires a PostgreSQL/Supabase URL outside --smoke mode "
                f"(got dialect {engine.dialect.name!r})."
            )
        schema = "benchmark_fixture_" + uuid4().hex
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                Base.metadata.create_all(connection)
                with Session(bind=connection) as session:
                    _seed_and_measure(
                        session,
                        engine=engine,
                        url=url,
                        term=term,
                        iterations=iterations,
                        sections=sections,
                    )
            finally:
                # Never commit the synthetic fixture: rolling back the transaction drops the
                # throwaway schema and every seeded row with it (D-04 -- never write synthetic
                # data into the real coverage database).
                transaction.rollback()
    finally:
        engine.dispose()


def _seed_and_measure(
    session: Session,
    *,
    engine: Engine,
    url: str | None,
    term: str,
    iterations: int,
    sections: int,
) -> None:
    now = datetime.now(UTC)
    seeded = _seed_synthetic_dataset(session, term_code=term, section_count=sections, now=now)
    session.flush()
    refreshed = refresh_section_rankings(session, term=term)
    session.flush()
    if refreshed != seeded:
        raise RuntimeError(
            f"Seeded {seeded} sections but refresh_section_rankings populated {refreshed} rows."
        )

    subjects_sample = list(SUBJECTS[: min(6, len(SUBJECTS))])
    durations: list[float] = []
    for query in _representative_queries(iterations=iterations, subjects=subjects_sample):
        start = time.perf_counter()
        search_rankings(
            term=term,
            session=session,
            subject=query.subject,
            seats_open=query.seats_open,
            min_easiness=query.min_easiness,
            sort=query.sort,
            limit=query.limit,
            offset=query.offset,
        )
        durations.append(time.perf_counter() - start)

    _report(durations=durations, dataset_size=refreshed, engine=engine, url=url)


def _seed_synthetic_dataset(
    session: Session, *, term_code: str, section_count: int, now: datetime
) -> int:
    term_id = 1
    prior_term_id = 2
    year, season = _term_year_season(term_code)
    prior_code = _prior_term_code(term_code)
    prior_year, prior_season = _term_year_season(prior_code)
    session.add_all(
        [
            Term(
                id=term_id,
                banner_code=term_code,
                name=f"{season} {year} (synthetic benchmark fixture)",
                year=year,
                season=season,
            ),
            Term(
                id=prior_term_id,
                banner_code=prior_code,
                name=f"{prior_season} {prior_year} (synthetic benchmark fixture, historical)",
                year=prior_year,
                season=prior_season,
            ),
        ]
    )
    session.flush()

    courses: list[Course] = []
    grades: list[GradeDistribution] = []
    sections: list[Section] = []
    instructors: list[SectionInstructor] = []
    snapshots: list[SeatSnapshot] = []

    course_index = 0
    section_id = 0
    sections_created = 0
    while sections_created < section_count:
        course_id = course_index + 1
        subject = SUBJECTS[course_index % len(SUBJECTS)]
        number = str(1000 + course_index)
        courses.append(
            Course(
                id=course_id,
                subject=subject,
                number=number,
                title=f"{subject} {number} (synthetic benchmark fixture course)",
                catalog_edition="benchmark-fixture",
            )
        )
        has_history = course_index % 3 != 0
        if has_history:
            grades.append(
                GradeDistribution(
                    term_id=prior_term_id,
                    crn=f"H{course_id}",
                    course_id=course_id,
                    section_number_raw="001",
                    section_suffix_raw=None,
                    campus_raw="Tampa",
                    a_count=40,
                    b_count=20,
                    c_count=10,
                    d_count=2,
                    f_count=1,
                    i_count=0,
                    s_count=0,
                    u_count=0,
                    w_count=3,
                    other_count=0,
                    total_grades=76,
                    source=f"benchmark-fixture-{course_id}",
                    source_hash=f"benchmark-fixture-{course_id}",
                )
            )

        remaining = section_count - sections_created
        n_this_course = min(SECTIONS_PER_COURSE, remaining)
        for offset in range(n_this_course):
            section_id += 1
            crn = str(100000 + section_id)
            has_instructor = section_id % 4 != 0
            delivery_method = "CL" if section_id % 2 == 0 else "ONL"
            seats_remaining = section_id % 40
            sections.append(
                Section(
                    id=section_id,
                    term_id=term_id,
                    crn=crn,
                    course_id=course_id,
                    section_number=f"{offset + 1:03d}",
                    campus="Tampa",
                    session="Full Term",
                    section_type="Class Lecture",
                    primary_status="Active",
                    delivery_method=delivery_method,
                    capacity=40,
                    enrollment=40 - seats_remaining,
                    seats_remaining=seats_remaining,
                    wait_seats_available=0,
                    first_seen_at=now,
                    last_seen_at=now,
                )
            )
            if has_instructor:
                instructor_name = f"Synthetic Fixture Instructor {section_id}"
                instructors.append(
                    SectionInstructor(
                        section_id=section_id,
                        name_raw=instructor_name,
                        name_normalized=instructor_name.lower(),
                        source="benchmark-fixture",
                        observed_at=now,
                    )
                )
            if section_id % 5 != 0:
                snapshots.append(
                    SeatSnapshot(
                        section_id=section_id,
                        observed_at=now,
                        capacity=40,
                        enrollment=40 - seats_remaining,
                        seats_remaining=seats_remaining,
                        wait_seats_available=0,
                    )
                )
            sections_created += 1
        course_index += 1

    session.add_all(courses)
    session.flush()
    session.add_all(grades)
    session.add_all(sections)
    session.add_all(instructors)
    session.add_all(snapshots)
    session.flush()
    return sections_created


def _representative_queries(
    *, iterations: int, subjects: list[str]
) -> list[_SearchQuery]:
    sorts = list(RankingSort)
    queries: list[_SearchQuery] = []
    for i in range(iterations):
        queries.append(
            _SearchQuery(
                subject=subjects[i % len(subjects)] if i % 3 == 0 else None,
                seats_open=i % 4 == 0,
                min_easiness=3.0 if i % 6 == 0 else None,
                sort=sorts[i % len(sorts)],
                limit=50,
                offset=(i % 5) * 50,
            )
        )
    return queries


def _report(
    *, durations: list[float], dataset_size: int, engine: Engine, url: str | None
) -> None:
    if not durations:
        raise RuntimeError("No search iterations were measured.")
    sorted_durations = sorted(durations)
    p50 = _percentile(sorted_durations, 0.50)
    p95 = _percentile(sorted_durations, 0.95)
    p_max = sorted_durations[-1]
    dialect = engine.dialect.name
    pooler = bool(url is not None and dialect == "postgresql" and is_transaction_pooler(url))
    environment = _environment_label(dialect=dialect, url=url)

    print(f"Dataset size: {dataset_size} sections (synthetic test fixture)")
    print(f"Environment: dialect={dialect}, pooler={pooler}, {environment}")
    print(f"Iterations: {len(durations)}")
    print(
        f"p50: {p50 * 1000:.2f}ms "
        f"(dataset size: {dataset_size} sections; environment: {environment})"
    )
    print(
        f"p95: {p95 * 1000:.2f}ms "
        f"(dataset size: {dataset_size} sections; environment: {environment})"
    )
    print(
        f"max: {p_max * 1000:.2f}ms "
        f"(dataset size: {dataset_size} sections; environment: {environment})"
    )


def _environment_label(*, dialect: str, url: str | None) -> str:
    is_supabase = url is not None and (
        is_transaction_pooler(url) or "supabase.com" in (make_url(url).host or "").lower()
    )
    if dialect == "sqlite":
        target = "SQLite"
    elif is_supabase:
        target = "Supabase"
    elif dialect == "postgresql":
        target = "local Postgres"
    else:
        target = dialect
    return f"synthetic test fixture over {target}"


def _percentile(sorted_values: list[float], pct: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * pct
    floor_index = math.floor(k)
    ceil_index = math.ceil(k)
    if floor_index == ceil_index:
        return sorted_values[int(k)]
    lower = sorted_values[floor_index] * (ceil_index - k)
    upper = sorted_values[ceil_index] * (k - floor_index)
    return lower + upper


def _term_year_season(code: str) -> tuple[int, str]:
    year = int(code[:4])
    season = _SUFFIX_TO_SEASON.get(code[4:6], "Fall")
    return year, season


def _prior_term_code(term_code: str) -> str:
    return f"{int(term_code) - 100:06d}"


def _term_code(value: str) -> str:
    try:
        return normalize_banner_term_code(value)
    except TermParseError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
