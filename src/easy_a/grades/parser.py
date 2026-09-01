from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from numbers import Integral, Real
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, field_validator

GRADE_BUCKETS = ("A", "B", "C", "D", "F", "I", "S", "U", "W", "O")
GRADE_COUNT_FIELDS = {
    "A": "a_count",
    "B": "b_count",
    "C": "c_count",
    "D": "d_count",
    "F": "f_count",
    "I": "i_count",
    "S": "s_count",
    "U": "u_count",
    "W": "w_count",
    "O": "other_count",
}


class SectionIdentifierParseError(ValueError):
    """Raised when a section identifier does not match the InfoCenter section shape."""


class GradeWorkbookSchemaError(ValueError):
    """Raised when a workbook is missing required structural columns."""


class GradeRowValidationError(BaseModel):
    row_number: int
    course: str
    message: str

    model_config = ConfigDict(frozen=True)


class GradeWorkbookValidationError(ValueError):
    def __init__(self, errors: Sequence[GradeRowValidationError], records_seen: int) -> None:
        self.errors = tuple(errors)
        self.records_seen = records_seen
        message = "; ".join(
            f"row {error.row_number} ({error.course}): {error.message}" for error in errors
        )
        super().__init__(message or "Grade workbook validation failed.")


class SectionIdentifier(BaseModel):
    subject: str
    course_number: str
    section_number: str
    section_suffix: str | None = None
    crn: str

    model_config = ConfigDict(frozen=True)

    @field_validator("subject", "course_number", "section_number", "section_suffix", "crn")
    @classmethod
    def normalize_identifier_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class ParsedGradeDistribution(BaseModel):
    row_number: int
    subject: str
    course_number: str
    section_number_raw: str
    section_suffix_raw: str | None = None
    crn: str
    campus_raw: str | None = None
    a_count: int = 0
    b_count: int = 0
    c_count: int = 0
    d_count: int = 0
    f_count: int = 0
    i_count: int = 0
    s_count: int = 0
    u_count: int = 0
    w_count: int = 0
    other_count: int = 0
    total_grades: int

    model_config = ConfigDict(frozen=True)

    @field_validator("subject", "course_number", "section_number_raw", "section_suffix_raw", "crn")
    @classmethod
    def normalize_record_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @property
    def count_sum(self) -> int:
        return (
            self.a_count
            + self.b_count
            + self.c_count
            + self.d_count
            + self.f_count
            + self.i_count
            + self.s_count
            + self.u_count
            + self.w_count
            + self.other_count
        )


_SECTION_IDENTIFIER_RE = re.compile(
    r"^\s*(?P<subject>[A-Za-z]{2,4})\s*-\s*(?P<number>\d{4}[A-Za-z]?)"
    r"\s*-\s*(?P<section>[A-Za-z0-9]+)(?:-(?P<suffix>[A-Za-z0-9]+))?"
    r"\s*\((?P<crn>\d+)\)\s*$"
)
_CAMPUS_ROW_RE = re.compile(r"^\s*\d{4}\s*-\s*.+campus\s*$", re.IGNORECASE)


def parse_section_identifier(raw_identifier: str) -> SectionIdentifier:
    match = _SECTION_IDENTIFIER_RE.match(raw_identifier)
    if match is None:
        raise SectionIdentifierParseError(f"Could not parse section identifier {raw_identifier!r}.")
    return SectionIdentifier(
        subject=match.group("subject"),
        course_number=match.group("number"),
        section_number=match.group("section"),
        section_suffix=match.group("suffix"),
        crn=match.group("crn"),
    )


def parse_grade_workbook(
    path: str | Path, sheet_name: str | int = 0
) -> list[ParsedGradeDistribution]:
    dataframe = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl", dtype=object)
    if not isinstance(dataframe, pd.DataFrame):
        raise GradeWorkbookSchemaError("Expected a single worksheet, not multiple worksheets.")
    return parse_grade_dataframe(dataframe)


def parse_grade_dataframe(dataframe: pd.DataFrame) -> list[ParsedGradeDistribution]:
    columns = _resolve_columns(dataframe.columns)
    records: list[ParsedGradeDistribution] = []
    errors: list[GradeRowValidationError] = []
    current_campus: str | None = None
    records_seen = 0

    for row_number, (_, row) in enumerate(dataframe.iterrows(), start=2):
        course_text = _cell_to_text(row[columns["course"]])
        if not course_text:
            continue
        if _CAMPUS_ROW_RE.match(course_text):
            current_campus = course_text
            continue

        try:
            section_identifier = parse_section_identifier(course_text)
        except SectionIdentifierParseError:
            continue

        records_seen += 1
        try:
            counts = {
                bucket: _cell_to_int(row[columns[bucket]], row_number, bucket)
                for bucket in GRADE_BUCKETS
            }
            total_grades = _cell_to_int(row[columns["total_grades"]], row_number, "Total Grades")
        except ValueError as exc:
            errors.append(
                GradeRowValidationError(
                    row_number=row_number,
                    course=course_text,
                    message=str(exc),
                )
            )
            continue

        count_sum = sum(counts.values())
        if count_sum != total_grades:
            errors.append(
                GradeRowValidationError(
                    row_number=row_number,
                    course=course_text,
                    message=f"count sum {count_sum} does not equal Total Grades {total_grades}",
                )
            )
            continue

        records.append(
            ParsedGradeDistribution(
                row_number=row_number,
                subject=section_identifier.subject,
                course_number=section_identifier.course_number,
                section_number_raw=section_identifier.section_number,
                section_suffix_raw=section_identifier.section_suffix,
                crn=section_identifier.crn,
                campus_raw=current_campus,
                a_count=counts["A"],
                b_count=counts["B"],
                c_count=counts["C"],
                d_count=counts["D"],
                f_count=counts["F"],
                i_count=counts["I"],
                s_count=counts["S"],
                u_count=counts["U"],
                w_count=counts["W"],
                other_count=counts["O"],
                total_grades=total_grades,
            )
        )

    if errors:
        raise GradeWorkbookValidationError(errors, records_seen=records_seen)

    return records


def _resolve_columns(columns: Iterable[Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    aliases = {"course": "course", "total grades": "total_grades"} | {
        bucket.lower(): bucket for bucket in GRADE_BUCKETS
    }

    for column in columns:
        canonical_name = aliases.get(_normalize_column_header(column))
        if canonical_name is not None and canonical_name not in resolved:
            resolved[canonical_name] = column

    missing = {"course", *GRADE_BUCKETS, "total_grades"} - resolved.keys()
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise GradeWorkbookSchemaError(f"Workbook is missing required columns: {missing_text}.")
    return resolved


def _normalize_column_header(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ").strip().lower())


def _cell_to_text(value: Any) -> str:
    if _is_empty_cell(value):
        return ""
    return str(value).strip()


def _cell_to_int(value: Any, row_number: int, column_name: str) -> int:
    if _is_empty_cell(value):
        return 0
    if isinstance(value, bool):
        raise ValueError(f"{column_name} contains a boolean at row {row_number}")
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        float_value = float(value)
        if float_value.is_integer():
            return int(float_value)
        raise ValueError(f"{column_name} contains non-integer value {value!r} at row {row_number}")

    text = str(value).strip().replace(",", "")
    if not text:
        return 0
    try:
        numeric_value = float(text)
    except ValueError as exc:
        raise ValueError(
            f"{column_name} contains non-numeric value {value!r} at row {row_number}"
        ) from exc
    if not numeric_value.is_integer():
        raise ValueError(f"{column_name} contains non-integer value {value!r} at row {row_number}")
    return int(numeric_value)


def _is_empty_cell(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False
