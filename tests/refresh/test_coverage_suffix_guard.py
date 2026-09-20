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


def test_suffix_variants_are_excluded_before_scope_validation(db_session: Session) -> None:
    config = _chm_config(db_session)

    try:
        rows = refresh_targets(
            db_session,
            term="202701",
            config=config,
            search=lambda query: _mixed_chm_response(query),
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


def test_non_tampa_exact_course_row_still_fails_scope_guard(db_session: Session) -> None:
    config = _chm_config(db_session)

    with pytest.raises(ValueError, match="Tampa/course/CRN scope"):
        refresh_targets(
            db_session,
            term="202701",
            config=config,
            search=lambda query: _mixed_chm_response(query, non_tampa_exact=True),
            observed_at=NOW,
        )

    assert not list(db_session.scalars(select(Section)))


def _chm_config(session: Session) -> CourseTargets:
    session.add(
        Course(
            subject="CHM",
            number="2045",
            title="General Chemistry I",
            catalog_edition="2026-2027",
        )
    )
    session.flush()
    return CourseTargets(
        catalog_edition="2026-2027",
        catalog_url_template="https://example.test/{subject}/{number}",
        targets=(CourseTarget(subject="CHM", number="2045"),),
    )


def _mixed_chm_response(
    query: ScheduleSearchQuery,
    *,
    non_tampa_exact: bool = False,
) -> str:
    assert (query.subject, query.course, query.campus) == ("CHM", "2045", "T")
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
        cells[4].string = "CHM 2045"
        if non_tampa_exact and index == 3:
            cells[21].string = "St. Petersburg"
        table.append(row)

    suffix_row = BeautifulSoup(template_html, "lxml").find("tr")
    assert isinstance(suffix_row, Tag)
    suffix_cells = suffix_row.find_all("td", recursive=False)
    suffix_cells[3].string = "21999"
    suffix_cells[4].string = "CHM 2045L"
    table.append(suffix_row)
    return str(soup)
