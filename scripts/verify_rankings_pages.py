"""Read-only, loopback-only full-page identity scanner for REQ-COVERAGE-03.

This script proves -- or explicitly disproves -- that every stored Section for a term
can actually be found through a complete walk of ``GET /api/v1/rankings/search``, not
only through a matching aggregate ``total``. The existing benchmark harness
(``scripts/benchmark_rankings_search.py``) checks only a first-page total; this scanner
walks every page with ``sort=course`` (a total order on ``(subject, course_number, crn)``
because ``crn`` is unique within a term -- ``uq_sections_term_crn``,
``uq_section_rankings_section_id``) and compares the exact identity set observed through
the API against the identity set stored in ``Section``.

Read-only and loopback-only: the stored-side query uses ``SET TRANSACTION READ ONLY`` on
PostgreSQL (matching ``scripts/benchmark_rankings_search.py``'s ``_run_live``), and
``--http-base-url`` must resolve to a plain loopback origin. No ranking calculation,
cache row or response field is read, written or changed (D-02). The connection string,
credentials and hostname are never printed -- only a sanitized dialect/host-class label
(matching ``_environment_label`` in the benchmark harness).

Exit codes: 0 PASS, 1 FAIL, 3 NOT MEASURED (the database or the HTTP target was
unreachable; the live path was not proven, and that must be recorded as such, never as
PASS).
"""

from __future__ import annotations

import argparse
import ipaddress
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from easy_a.api.schemas import RankingsSearchResponse
from easy_a.common.campus import SUPPORTED_CAMPUS, same_campus
from easy_a.common.terms import TermParseError, normalize_banner_term_code
from easy_a.db import get_engine
from easy_a.models import Section, SectionRankingCache, Term

GATE = "api_identity"
DEFAULT_TERM = "202701"
DEFAULT_PAGE_SIZE = 200
MAX_PAGE_SIZE = 200
SAMPLE_CAP = 20
SEARCH_PATH = "/api/v1/rankings/search"

OrderKey = tuple[str, str, str]


@dataclass(frozen=True)
class StoredSnapshot:
    """The identity set actually stored for a term, read once, read-only."""

    identities: frozenset[str]
    cache_count: int
    non_tampa_count: int


@dataclass(frozen=True)
class PageScan:
    """The result of walking every search page for a term."""

    order_keys: tuple[OrderKey, ...]
    api_total: int | None
    pages_fetched: int
    score_source_counts: dict[str, int]
    effective_n_zero_counts: dict[str, int]
    reason: str | None


@dataclass(frozen=True)
class IdentityVerdict:
    """PASS/FAIL comparison of a StoredSnapshot against a PageScan."""

    verdict: str
    reason: str | None
    missing: frozenset[str] = frozenset()
    extra: frozenset[str] = frozenset()
    duplicates: tuple[str, ...] = ()


class _ScanStop(Exception):
    """Internal signal: the page walk cannot continue; carries the FAIL reason."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def stored_identities(session: Session, *, term: str) -> StoredSnapshot:
    """Read the stored (term, crn) identity set for ``term`` in one read-only session."""
    normalized_term = normalize_banner_term_code(term)
    bind = session.get_bind()
    if getattr(getattr(bind, "dialect", None), "name", None) == "postgresql":
        session.execute(text("SET TRANSACTION READ ONLY"))
    rows = session.execute(
        select(Section.crn, Section.campus)
        .join(Term, Section.term_id == Term.id)
        .where(Term.banner_code == normalized_term)
    ).all()
    identities = frozenset(crn for crn, _campus in rows)
    non_tampa_count = sum(1 for _crn, campus in rows if not same_campus(campus, SUPPORTED_CAMPUS))
    cache_count = (
        session.scalar(
            select(func.count())
            .select_from(SectionRankingCache)
            .where(SectionRankingCache.term == normalized_term)
        )
        or 0
    )
    return StoredSnapshot(
        identities=identities,
        cache_count=cache_count,
        non_tampa_count=non_tampa_count,
    )


def _fetch_page(
    client: httpx.Client, term: str, page_size: int, offset: int
) -> RankingsSearchResponse:
    response = client.get(
        SEARCH_PATH,
        params={"term": term, "sort": "course", "limit": page_size, "offset": offset},
    )
    if response.status_code != 200:
        raise _ScanStop("http_status", f"HTTP {response.status_code} at offset {offset}")
    try:
        body = response.json()
    except ValueError:
        raise _ScanStop("invalid_response", f"non-JSON body at offset {offset}") from None
    try:
        parsed = RankingsSearchResponse.model_validate(body)
    except Exception:
        raise _ScanStop(
            "invalid_response", f"schema validation failed at offset {offset}"
        ) from None
    if parsed.limit != page_size or parsed.offset != offset or len(parsed.items) > page_size:
        raise _ScanStop("invalid_response", f"pagination echo mismatch at offset {offset}")
    return parsed


def _order_violation(previous_keys: list[OrderKey], page_keys: list[OrderKey]) -> str | None:
    """Compare (subject, course_number, crn) ordering; crn is unique within a term, so
    the order is total. Equal adjacent keys are a repeated identity, not a swap."""
    if previous_keys and page_keys:
        if previous_keys[-1] == page_keys[0]:
            return "duplicate_identity"
        if previous_keys[-1] > page_keys[0]:
            return "order_violation"
    for i in range(len(page_keys) - 1):
        if page_keys[i] == page_keys[i + 1]:
            return "duplicate_identity"
        if page_keys[i] > page_keys[i + 1]:
            return "order_violation"
    return None


def scan_pages(client: httpx.Client, term: str, page_size: int) -> PageScan:
    """Walk every page of GET /api/v1/rankings/search with sort=course.

    Stops after ceil(first_total / page_size) pages (or 1 page when the first-observed
    total is 0), bounding the walk by the total the API itself reported on the first
    page. Any total that changes between pages, any page shorter than expected before
    the total is reached, and any page that collectively yields more items than the
    first-observed total each stop the walk immediately with a named reason -- a
    partial or unstable scan is never reported as PASS.
    """
    order_keys: list[OrderKey] = []
    score_source_counts: dict[str, int] = {}
    effective_n_zero_counts: dict[str, int] = {}
    first_total: int | None = None
    collected = 0
    page_index = 0
    pages_fetched = 0
    reason: str | None = None

    while True:
        offset = page_index * page_size
        try:
            page = _fetch_page(client, term, page_size, offset)
        except _ScanStop as stop:
            reason = stop.reason
            break

        pages_fetched += 1
        if first_total is None:
            first_total = page.total
        elif page.total != first_total:
            reason = "snapshot_changed"
            break

        page_keys: list[OrderKey] = [
            (item.subject, item.course_number, item.crn) for item in page.items
        ]
        violation = _order_violation(order_keys, page_keys)
        if violation is not None:
            reason = violation
            break

        for item in page.items:
            source = item.score_source.value
            score_source_counts[source] = score_source_counts.get(source, 0) + 1
            if item.effective_n == 0:
                effective_n_zero_counts[source] = effective_n_zero_counts.get(source, 0) + 1

        order_keys.extend(page_keys)
        collected += len(page.items)

        if collected > first_total:
            reason = "page_overrun"
            break
        if collected == first_total:
            break
        if len(page.items) < page_size:
            reason = "short_page"
            break
        page_index += 1

    return PageScan(
        order_keys=tuple(order_keys),
        api_total=first_total,
        pages_fetched=pages_fetched,
        score_source_counts=score_source_counts,
        effective_n_zero_counts=effective_n_zero_counts,
        reason=reason,
    )


def reconcile(stored: StoredSnapshot, scan: PageScan) -> IdentityVerdict:
    """Compare a StoredSnapshot against a PageScan. PASS requires stored_count ==
    cache_count == api_total, non_tampa_count == 0, and exact identity-set equality."""
    if scan.reason is not None:
        return IdentityVerdict(verdict="FAIL", reason=scan.reason)

    scanned_crns = [key[2] for key in scan.order_keys]
    seen: set[str] = set()
    duplicates: list[str] = []
    for crn in scanned_crns:
        if crn in seen:
            duplicates.append(crn)
        seen.add(crn)
    if duplicates:
        return IdentityVerdict(
            verdict="FAIL", reason="duplicate_identity", duplicates=tuple(duplicates)
        )

    scanned_set = frozenset(scanned_crns)
    missing = stored.identities - scanned_set
    extra = scanned_set - stored.identities
    if missing or extra:
        return IdentityVerdict(
            verdict="FAIL",
            reason="identity_mismatch",
            missing=frozenset(missing),
            extra=frozenset(extra),
        )

    if stored.non_tampa_count > 0:
        return IdentityVerdict(verdict="FAIL", reason="non_tampa_section")

    stored_count = len(stored.identities)
    api_total = scan.api_total or 0
    if not (stored_count == stored.cache_count == api_total):
        return IdentityVerdict(verdict="FAIL", reason="count_mismatch")

    return IdentityVerdict(verdict="PASS", reason=None)


def _http_base_url(value: str) -> str:
    """Same plain-loopback-origin validation semantics as
    scripts/benchmark_rankings_search.py's ``_http_base_url``: scheme http, host is
    localhost or a loopback IP, no credentials, no path/query/fragment."""
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


def _environment_label(engine: Engine) -> str:
    dialect = engine.dialect.name
    if dialect == "sqlite":
        return "SQLite"
    if dialect != "postgresql":
        return dialect
    host = (engine.url.host or "").lower()
    if host.endswith((".supabase.com", ".supabase.co")):
        return "Supabase"
    return "Postgres (other host)"


def _term_code(value: str) -> str:
    try:
        return normalize_banner_term_code(value)
    except TermParseError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _page_size(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if not (1 <= parsed <= MAX_PAGE_SIZE):
        raise argparse.ArgumentTypeError(f"must be between 1 and {MAX_PAGE_SIZE}")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only, loopback-only full-page identity scanner for REQ-COVERAGE-03. "
            "Walks GET /api/v1/rankings/search with sort=course (a total order on "
            "subject, course_number, crn -- crn is unique within a term) across every "
            "page and proves exact identity-set equality between stored Section rows "
            "and the API, rather than trusting a matching aggregate total alone. Never "
            "changes the scoring model, cached rankings or the RankingsSearchResponse "
            "contract. Exit codes: 0 PASS, 1 FAIL, 3 NOT MEASURED (database or HTTP "
            "target unreachable)."
        )
    )
    parser.add_argument(
        "--term",
        type=_term_code,
        default=DEFAULT_TERM,
        help=f"Banner term code to scan. Default: {DEFAULT_TERM}.",
    )
    parser.add_argument(
        "--http-base-url",
        required=True,
        help=(
            "Loopback API base URL, e.g. http://127.0.0.1:8000. Must resolve to a "
            "plain loopback origin (rejected before any network request otherwise)."
        ),
    )
    parser.add_argument(
        "--page-size",
        type=_page_size,
        default=DEFAULT_PAGE_SIZE,
        help=f"Rows per page, 1..{MAX_PAGE_SIZE} (matches the route's limit bound). "
        f"Default: {DEFAULT_PAGE_SIZE}.",
    )
    return parser


def _not_measured(*, term: str, page_size: int, environment: str, reason: str) -> dict[str, Any]:
    return {
        "gate": GATE,
        "verdict": "NOT MEASURED",
        "reason": reason,
        "term": term,
        "observed_at_utc": datetime.now(UTC).isoformat(),
        "environment": environment,
        "stored_count": None,
        "cache_count": None,
        "api_total": None,
        "pages_fetched": 0,
        "page_size": page_size,
        "missing_count": None,
        "extra_count": None,
        "duplicate_count": None,
        "non_tampa_count": None,
        "order_violations": 0,
        "sample_missing": [],
        "sample_extra": [],
        "sample_duplicates": [],
        "api_score_source_split": {},
    }


def _build_output(
    *,
    term: str,
    page_size: int,
    environment: str,
    stored: StoredSnapshot,
    scan: PageScan,
    verdict: IdentityVerdict,
) -> dict[str, Any]:
    score_source_split = {
        source: {"count": count, "effective_n_zero": scan.effective_n_zero_counts.get(source, 0)}
        for source, count in sorted(scan.score_source_counts.items())
    }
    return {
        "gate": GATE,
        "verdict": verdict.verdict,
        "reason": verdict.reason,
        "term": term,
        "observed_at_utc": datetime.now(UTC).isoformat(),
        "environment": environment,
        "stored_count": len(stored.identities),
        "cache_count": stored.cache_count,
        "api_total": scan.api_total,
        "pages_fetched": scan.pages_fetched,
        "page_size": page_size,
        "missing_count": len(verdict.missing),
        "extra_count": len(verdict.extra),
        "duplicate_count": len(verdict.duplicates),
        "non_tampa_count": stored.non_tampa_count,
        "order_violations": 1 if scan.reason == "order_violation" else 0,
        "sample_missing": sorted(verdict.missing)[:SAMPLE_CAP],
        "sample_extra": sorted(verdict.extra)[:SAMPLE_CAP],
        "sample_duplicates": sorted(set(verdict.duplicates))[:SAMPLE_CAP],
        "api_score_source_split": score_source_split,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        base_url = _http_base_url(args.http_base_url)
    except ValueError:
        parser.error("HTTP target must be a plain loopback origin")
        return 2  # pragma: no cover - parser.error() exits the process above.

    engine = get_engine()
    environment = _environment_label(engine)
    try:
        with Session(engine) as session:
            try:
                stored = stored_identities(session, term=args.term)
            except SQLAlchemyError:
                print(
                    json.dumps(
                        _not_measured(
                            term=args.term,
                            page_size=args.page_size,
                            environment=environment,
                            reason="db_unreachable",
                        )
                    )
                )
                return 3

            with httpx.Client(
                base_url=base_url, timeout=60, trust_env=False, follow_redirects=False
            ) as client:
                try:
                    scan = scan_pages(client, args.term, args.page_size)
                except httpx.HTTPError:
                    print(
                        json.dumps(
                            _not_measured(
                                term=args.term,
                                page_size=args.page_size,
                                environment=environment,
                                reason="http_unreachable",
                            )
                        )
                    )
                    return 3
    finally:
        engine.dispose()

    verdict = reconcile(stored, scan)
    output = _build_output(
        term=args.term,
        page_size=args.page_size,
        environment=environment,
        stored=stored,
        scan=scan,
        verdict=verdict,
    )
    print(json.dumps(output))
    return 0 if verdict.verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
