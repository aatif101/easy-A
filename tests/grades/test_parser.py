from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from easy_a.grades.parser import (
    GradeWorkbookValidationError,
    parse_grade_workbook,
    parse_section_identifier,
)

GRADE_HEADER = [
    "course",
    "A",
    "% A",
    "B",
    "% B",
    "C",
    "% C",
    "D",
    "% D",
    "F",
    "% F",
    "I",
    "% I",
    "S",
    "% S",
    "U",
    "% U",
    "W",
    "% W",
    "O",
    "% O",
    "Total Grades",
]


def test_parse_section_identifier_example() -> None:
    identifier = parse_section_identifier("MAC-1105 -001-C (89033)")

    assert identifier.subject == "MAC"
    assert identifier.course_number == "1105"
    assert identifier.section_number == "001"
    assert identifier.section_suffix == "C"
    assert identifier.crn == "89033"


def test_grade_workbook_ignores_hierarchy_and_total_rows(tmp_path: Path) -> None:
    workbook_path = tmp_path / "synthetic_grade_distribution.xlsx"
    _write_workbook(
        workbook_path,
        [
            _hierarchy_row("0001 - Tampa Campus"),
            _hierarchy_row("College of Arts and Sciences"),
            _hierarchy_row("CAS MATHEMATICS & STATISTICS"),
            _grade_row("MAC-1105 -001-C (89033)", a=10, b=4, w=1, total=15),
            _hierarchy_row("Total CAS MATHEMATICS & STATISTICS"),
            _hierarchy_row("Total College of Arts and Sciences"),
            _hierarchy_row("Total 0001 - Tampa Campus"),
        ],
    )

    records = parse_grade_workbook(workbook_path)

    assert len(records) == 1
    assert records[0].crn == "89033"
    assert records[0].campus_raw == "0001 - Tampa Campus"


def test_valid_count_sum_succeeds(tmp_path: Path) -> None:
    workbook_path = tmp_path / "valid_counts.xlsx"
    _write_workbook(
        workbook_path,
        [_grade_row("MAC-1105 -001-C (89033)", a=3, b=2, c=1, o=1, total=7)],
    )

    records = parse_grade_workbook(workbook_path)

    assert len(records) == 1
    assert records[0].count_sum == 7
    assert records[0].total_grades == 7


def test_invalid_total_fails(tmp_path: Path) -> None:
    workbook_path = tmp_path / "invalid_total.xlsx"
    _write_workbook(
        workbook_path,
        [_grade_row("MAC-1105 -001-C (89033)", a=3, b=2, total=99)],
    )

    with pytest.raises(GradeWorkbookValidationError) as exc_info:
        parse_grade_workbook(workbook_path)

    assert "count sum 5 does not equal Total Grades 99" in str(exc_info.value)


def test_empty_count_cells_are_zero(tmp_path: Path) -> None:
    workbook_path = tmp_path / "empty_cells.xlsx"
    _write_workbook(
        workbook_path,
        [_grade_row("MAC-1105 -001-C (89033)", a=2, b=None, c="", w=1, total=3)],
    )

    records = parse_grade_workbook(workbook_path)

    assert records[0].b_count == 0
    assert records[0].c_count == 0
    assert records[0].w_count == 1
    assert records[0].total_grades == 3


def _write_workbook(path: Path, rows: list[list[object]]) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    assert worksheet is not None
    worksheet.append(GRADE_HEADER)
    for row in rows:
        worksheet.append(row)
    workbook.save(path)


def _hierarchy_row(label: str) -> list[object]:
    return [label, *([None] * (len(GRADE_HEADER) - 1))]


def _grade_row(
    course: str,
    *,
    a: object = 0,
    b: object = 0,
    c: object = 0,
    d: object = 0,
    f: object = 0,
    i: object = 0,
    s: object = 0,
    u: object = 0,
    w: object = 0,
    o: object = 0,
    total: object = 0,
) -> list[object]:
    return [
        course,
        a,
        None,
        b,
        None,
        c,
        None,
        d,
        None,
        f,
        None,
        i,
        None,
        s,
        None,
        u,
        None,
        w,
        None,
        o,
        None,
        total,
    ]
