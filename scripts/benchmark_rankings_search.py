"""Benchmark rankings search on stored data or a rolled-back synthetic fixture.

This is a repeatable, offline-capable performance harness for REQ-PERF-01. It seeds a
parameterized number of synthetic sections -- clearly labeled a test fixture -- and times
representative rankings-search queries against the rewritten cache-backed search path
(Phase 03.5 Plan 02), printing p50/p95/max latency with the dataset size and environment on
every reported number.

Two run modes:
- ``--live``: read-only stored-term route diagnosis. Add ``--http-base-url`` for
  loopback HTTP measurement against an API started with the same DATABASE_URL.
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
import ipaddress
import json
import math
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from easy_a.api.routes.rankings import search_rankings
from easy_a.api.schemas import RankingSort, RankingsSearchResponse
from easy_a.common.terms import TermParseError, normalize_banner_term_code
from easy_a.db import Base, get_engine
from easy_a.models import Course, GradeDistribution, SeatSnapshot, Section, SectionInstructor, Term
from easy_a.rankings.cache import SectionRankingCache, refresh_section_rankings

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
    parser.add_argument(
        "--live",
        action="store_true",
        help="Read-only stored-term measurement; no synthetic fixture.",
    )
    parser.add_argument(
        "--http-base-url", help="Loopback API served with the same DATABASE_URL as this process."
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.iterations > 10000:
        parser.error("iterations must not exceed 10000")
    if args.live and (args.smoke or args.iterations < 50):
        parser.error("--live requires at least 50 iterations and cannot use --smoke")
    if args.http_base_url and not args.live:
        parser.error("--http-base-url requires --live")
    if args.http_base_url:
        try:
            args.http_base_url = _http_base_url(args.http_base_url)
        except ValueError:
            parser.error("HTTP target must be a plain loopback origin")
    if args.live:
        try:
            _run_live(
                term=args.term,
                iterations=args.iterations,
                url=args.url,
                http_base_url=args.http_base_url,
            )
        except Exception as exc:
            # Driver/HTTP exception strings can include connection targets and secrets.
            print(
                f"Live benchmark failed ({type(exc).__name__}); no result claimed.", file=sys.stderr
            )
            return 1
        return 0
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


def _http_base_url(value: str) -> str:
    parsed = urlsplit(value)
    host = parsed.hostname
    try:
        loopback = host == "localhost" or ipaddress.ip_address(host or "").is_loopback
        _ = parsed.port  # Validate malformed ports without printing the supplied URL.
    except ValueError:
        loopback = False
    if (
        parsed.scheme != "http"
        or not loopback
        or parsed.username
        or parsed.password
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("HTTP target must be a plain loopback origin")
    return value.rstrip("/")


def _query_params(term: str, query: _SearchQuery) -> dict:
    return {
        k: v
        for k, v in {
            "term": term,
            "subject": query.subject,
            "seats_open": query.seats_open,
            "min_easiness": query.min_easiness,
            "sort": query.sort.value,
            "limit": query.limit,
            "offset": query.offset,
        }.items()
        if v is not None
    }


def _http_search(
    client: httpx.Client, base_url: str, term: str, query: _SearchQuery
) -> RankingsSearchResponse:
    response = client.get(base_url + "/api/v1/rankings/search", params=_query_params(term, query))
    if response.status_code != 200:
        raise ValueError(f"HTTP search failed with status {response.status_code}")
    try:
        result = RankingsSearchResponse.model_validate(response.json())
    except ValueError:
        raise ValueError("Invalid HTTP search response") from None
    if (
        result.limit != query.limit
        or result.offset != query.offset
        or result.total < 0
        or len(result.items) > query.limit
    ):
        raise ValueError("HTTP search pagination mismatch")
    return result


def _run_live(*, term: str, iterations: int, url: str | None, http_base_url: str | None) -> None:
    engine = get_engine(url) if url else get_engine()
    engine.echo = False
    try:
        with (
            Session(engine) as session,
            httpx.Client(timeout=60, trust_env=False, follow_redirects=False) as client,
        ):
            if engine.dialect.name == "postgresql":
                session.execute(text("SET TRANSACTION READ ONLY"))
            stored = session.scalar(
                select(func.count()).select_from(Section).join(Term).where(Term.banner_code == term)
            )
            cached = session.scalar(
                select(func.count())
                .select_from(SectionRankingCache)
                .where(SectionRankingCache.term == term)
            )
            if not stored or cached != stored:
                raise ValueError("Stored section and cache counts must be nonzero and equal")
            queries = _representative_queries(iterations=iterations, subjects=list(SUBJECTS[:6]))
            mode = (
                "loopback HTTP request + body + JSON validation"
                if http_base_url
                else "in-process route diagnostic"
            )
            if http_base_url:
                broad = _SearchQuery(None, False, None, RankingSort.course, 50, 0)
                if _http_search(client, http_base_url, term, broad).total != stored:
                    raise ValueError("HTTP total does not reconcile with stored term")
            durations = []
            for i, query in enumerate(queries[:5] + queries):
                start = time.perf_counter()
                if http_base_url:
                    _http_search(client, http_base_url, term, query)
                else:
                    params = _query_params(term, query)
                    params["sort"] = query.sort
                    search_rankings(session=session, **params)
                elapsed = time.perf_counter() - start
                if i >= 5:
                    durations.append(elapsed)
            print(f"UTC: {datetime.now(UTC).isoformat()}; term={term}; warmup=5; mode={mode}")
            _report(
                durations=durations,
                dataset_size=cached,
                engine=engine,
                url=None,
                dataset="stored term",
                mode=mode,
            )
            for query, duration in zip(queries, durations, strict=True):
                print(
                    json.dumps(
                        {
                            "query": _query_params(term, query),
                            "elapsed_ms": round(duration * 1000, 3),
                        }
                    )
                )
            for sort in RankingSort:
                values = sorted(
                    d for q, d in zip(queries, durations, strict=True) if q.sort == sort
                )
                print(
                    f"sort={sort.value} count={len(values)} "
                    f"p50_ms={_percentile(values, 0.5) * 1000:.2f} "
                    f"p95_ms={_percentile(values, 0.95) * 1000:.2f} "
                    f"max_ms={max(values) * 1000:.2f}"
                )
    finally:
        engine.dispose()


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


def _run_against_postgres(*, term: str, iterations: int, sections: int, url: str | None) -> None:
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


def _representative_queries(*, iterations: int, subjects: list[str]) -> list[_SearchQuery]:
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
    *,
    durations: list[float],
    dataset_size: int,
    engine: Engine,
    url: str | None,
    dataset: str = "synthetic test fixture",
    mode: str = "in-process route diagnostic",
) -> None:
    if not durations:
        raise RuntimeError("No search iterations were measured.")
    sorted_durations = sorted(durations)
    p50 = _percentile(sorted_durations, 0.50)
    p95 = _percentile(sorted_durations, 0.95)
    p_max = sorted_durations[-1]
    dialect = engine.dialect.name
    resolved = engine.url
    pooler = dialect == "postgresql" and (
        resolved.port == 6543 or "pooler.supabase.com" in (resolved.host or "")
    )
    environment = _environment_label(dialect=dialect, url=resolved).replace(
        "synthetic test fixture", dataset
    )

    print(f"Dataset size: {dataset_size} sections ({dataset}); mode={mode}")
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
        (make_url(url).host or "").lower().endswith((".supabase.com", ".supabase.co"))
    )
    if dialect == "sqlite":
        target = "SQLite"
    elif is_supabase:
        target = "Supabase"
    elif dialect == "postgresql":
        target = "Postgres (other host)"
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
