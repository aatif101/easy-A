from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from easy_a.catalog.client import fetch_catalog_html
from easy_a.catalog.ingest import upsert_catalog_courses
from easy_a.catalog.parser import parse_catalog_html
from easy_a.common.terms import normalize_banner_term_code
from easy_a.models import Course, Section, Term
from easy_a.rankings.cache import refresh_section_rankings
from easy_a.refresh.targets import CourseTarget, CourseTargets
from easy_a.schedule.client import ScheduleSearchQuery
from easy_a.schedule.freshness import as_utc
from easy_a.schedule.ingest import ingest_schedule_html
from easy_a.schedule.parser import ParsedScheduleRow, parse_schedule_html


class TargetCoverage(BaseModel):
    subject: str
    course_number: str
    catalog_present: bool
    section_count: int
    latest_observed_at: datetime | None
    status: Literal["missing", "observed"]


class TargetRefresh(BaseModel):
    subject: str
    course_number: str
    catalog_present: bool
    section_count: int
    snapshots_added: int = 0


def coverage_metadata(
    session: Session, term: str, targets: tuple[CourseTarget, ...]
) -> list[TargetCoverage]:
    term = normalize_banner_term_code(term)
    result = []
    for target in targets:
        course_ids = select(Course.id).where(
            Course.subject == target.subject, Course.number == target.number
        )
        present = session.scalar(
            select(Course.id)
            .where(Course.subject == target.subject, Course.number == target.number)
            .limit(1)
        )
        count, observed = session.execute(
            select(func.count(Section.id), func.max(Section.last_seen_at))
            .join(Term)
            .where(Term.banner_code == term, Section.course_id.in_(course_ids))
        ).one()
        result.append(
            TargetCoverage(
                subject=target.subject,
                course_number=target.number,
                catalog_present=present is not None,
                section_count=count,
                latest_observed_at=as_utc(observed) if observed is not None else None,
                status="observed" if count else "missing",
            )
        )
    return result


def refresh_targets(
    session: Session,
    *,
    term: str,
    config: CourseTargets,
    search: Callable[[ScheduleSearchQuery], str],
    catalog_fetch: Callable[[str], str] = fetch_catalog_html,
    refresh_catalog: bool = False,
    subject: str | None = None,
    course: str | None = None,
    crn: str | None = None,
    observed_at: datetime | None = None,
) -> list[TargetRefresh]:
    """One sequential pass. Caller owns transaction; failures must roll it back."""
    term = normalize_banner_term_code(term)
    targets = config.select(subject, course)
    if crn is not None:
        if not crn.isdigit() or len(crn) != 5:
            raise ValueError("CRN must contain five digits.")
        row = session.execute(
            select(Course.subject, Course.number)
            .join(Section, Section.course_id == Course.id)
            .join(Term)
            .where(Term.banner_code == term, Section.crn == crn)
        ).one_or_none()
        if row is None:
            raise ValueError("CRN must already exist in this term; run coverage refresh first.")
        targets = tuple(t for t in targets if (t.subject, t.number) == tuple(row))
        if not targets:
            raise ValueError("CRN does not match the configured targets/filter.")
    results = []
    for target in targets:
        if refresh_catalog:
            html = catalog_fetch(
                config.catalog_url_template.format(subject=target.subject, number=target.number)
            )
            parsed = parse_catalog_html(html, config.catalog_edition)
            matching = [
                c for c in parsed if (c.subject, c.number) == (target.subject, target.number)
            ]
            if not matching:
                results.append(
                    TargetRefresh(
                        subject=target.subject,
                        course_number=target.number,
                        catalog_present=False,
                        section_count=0,
                    )
                )
                continue
            upsert_catalog_courses(session, matching)
        present = session.scalar(
            select(Course.id)
            .where(Course.subject == target.subject, Course.number == target.number)
            .limit(1)
        )
        if present is None:
            results.append(
                TargetRefresh(
                    subject=target.subject,
                    course_number=target.number,
                    catalog_present=False,
                    section_count=0,
                )
            )
            continue
        query = ScheduleSearchQuery(
            term=term, campus="T", subject=target.subject, course=target.number, crn=crn
        )
        html = search(query)
        parsed_rows = parse_schedule_html(html)
        # Suffix variants such as CHM 2045L are separate configurable targets when wanted.
        rows = [
            row
            for row in parsed_rows
            if (row.subject, row.course_number) == (target.subject, target.number)
        ]
        if any(
            r.campus.strip() != "Tampa" or (crn is not None and r.crn != crn)
            for r in rows
        ):
            raise ValueError("Schedule response exceeded the requested Tampa/course/CRN scope.")
        if len({r.crn for r in rows}) != len(rows):
            raise ValueError("Schedule response contains duplicate CRNs.")
        exact_html = _retain_exact_course_rows(
            html,
            parsed_rows=parsed_rows,
            subject=target.subject,
            course_number=target.number,
        )
        result = ingest_schedule_html(
            session, exact_html, term, observed_at=observed_at or datetime.now(UTC)
        )
        refresh_section_rankings(
            session,
            term=term,
            subject=target.subject,
            course_number=target.number,
        )
        results.append(
            TargetRefresh(
                subject=target.subject,
                course_number=target.number,
                catalog_present=True,
                section_count=result.records_seen,
                snapshots_added=result.seat_snapshots_created,
            )
        )
    return results


def _retain_exact_course_rows(
    html: str,
    *,
    parsed_rows: list[ParsedScheduleRow],
    subject: str,
    course_number: str,
) -> str:
    """Remove source rows excluded by the exact-course pre-filter before ingestion."""
    soup = BeautifulSoup(html, "lxml")
    header = next(
        (
            row
            for row in soup.find_all("tr")
            if isinstance(row, Tag) and len(row.find_all("th", recursive=False)) == 24
        ),
        None,
    )
    if header is None:
        return html
    html_rows = [
        row
        for row in header.find_all_next("tr")
        if isinstance(row, Tag) and len(row.find_all("td", recursive=False)) == 24
    ]
    if len(html_rows) != len(parsed_rows):
        raise ValueError("Parsed schedule rows no longer match the schedule response.")
    for html_row, parsed_row in zip(html_rows, parsed_rows, strict=True):
        if (parsed_row.subject, parsed_row.course_number) != (subject, course_number):
            html_row.decompose()
    return str(soup)
