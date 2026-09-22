from __future__ import annotations

import pytest
from bs4 import BeautifulSoup, Tag
from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.models import Course, Section
from easy_a.refresh.coverage import refresh_targets
from easy_a.refresh.targets import CourseTarget, CourseTargets
from easy_a.schedule.client import ScheduleSearchQuery
from tests.refresh.test_targets import FIXTURES, NOW

# A representative sample of the 33 base/suffix pairs in courses.csv (verified this session via
# data/coverage-pilot-2026-09-20/suffix-query-risks.json and a direct courses.csv scan), proving
# _retain_exact_course_rows generalizes beyond the single documented CHM 2045 case.
SUFFIX_PAIRS = (
    ("CHM", "2045", "2045L"),
    ("BSC", "2010", "2010L"),
    ("PHY", "2049", "2049L"),
    ("APK", "3125", "3125L"),
)


@pytest.mark.parametrize(("subject", "base_number", "suffix_number"), SUFFIX_PAIRS)
def test_suffix_variants_are_excluded_before_scope_validation(
    db_session: Session, subject: str, base_number: str, suffix_number: str
) -> None:
    config = _course_config(db_session, subject, base_number)

    try:
        rows = refresh_targets(
            db_session,
            term="202701",
            config=config,
            search=lambda query: _mixed_response(query, subject, base_number, suffix_number),
            observed_at=NOW,
        )
    except ValueError as exc:
        pytest.fail(f"suffix-only schedule rows must be excluded, not rejected: {exc}")

    assert rows[0].section_count == 5
    sections = db_session.scalars(select(Section).order_by(Section.crn)).all()
    assert len(sections) == 5
    assert {section.crn for section in sections} == {
        "21001",
        "21002",
        "21003",
        "21004",
        "21005",
    }


@pytest.mark.parametrize(("subject", "base_number", "suffix_number"), SUFFIX_PAIRS)
def test_non_tampa_exact_course_row_still_fails_scope_guard(
    db_session: Session, subject: str, base_number: str, suffix_number: str
) -> None:
    config = _course_config(db_session, subject, base_number)

    with pytest.raises(ValueError, match="Tampa/course/CRN scope"):
        refresh_targets(
            db_session,
            term="202701",
            config=config,
            search=lambda query: _mixed_response(
                query, subject, base_number, suffix_number, non_tampa_exact=True
            ),
            observed_at=NOW,
        )

    assert not list(db_session.scalars(select(Section)))


def _course_config(session: Session, subject: str, base_number: str) -> CourseTargets:
    session.add(
        Course(
            subject=subject,
            number=base_number,
            title=f"{subject} {base_number}",
            catalog_edition="2026-2027",
        )
    )
    session.flush()
    return CourseTargets(
        catalog_edition="2026-2027",
        catalog_url_template="https://example.test/{subject}/{number}",
        targets=(CourseTarget(subject=subject, number=base_number),),
    )


def _mixed_response(
    query: ScheduleSearchQuery,
    subject: str,
    base_number: str,
    suffix_number: str,
    *,
    non_tampa_exact: bool = False,
) -> str:
    assert (query.subject, query.course, query.campus) == (subject, base_number, "T")
    html = (FIXTURES / "schedule_current.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")
    source_rows = [row for row in soup.find_all("tr") if len(row.find_all("td")) == 24]
    assert source_rows
    template_html = str(source_rows[0])
    table = source_rows[0].find_parent("table")
    assert isinstance(table, Tag)
    for row in source_rows:
        row.decompose()

    for index in range(1, 6):
        row = BeautifulSoup(template_html, "lxml").find("tr")
        assert isinstance(row, Tag)
        cells = row.find_all("td", recursive=False)
        cells[3].string = f"2100{index}"
        cells[4].string = f"{subject} {base_number}"
        if non_tampa_exact and index == 3:
            cells[21].string = "St. Petersburg"
        table.append(row)

    suffix_row = BeautifulSoup(template_html, "lxml").find("tr")
    assert isinstance(suffix_row, Tag)
    suffix_cells = suffix_row.find_all("td", recursive=False)
    suffix_cells[3].string = "21999"
    suffix_cells[4].string = f"{subject} {suffix_number}"
    table.append(suffix_row)
    return str(soup)
