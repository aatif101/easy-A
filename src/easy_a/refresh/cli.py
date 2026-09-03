from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path

from easy_a.common.terms import TermParseError, normalize_banner_term_code
from easy_a.quality.checks import DEFAULT_STALE_AFTER_DAYS
from easy_a.refresh.models import (
    CatalogInput,
    GradeInput,
    RefreshConfig,
    RefreshConfigurationError,
    RefreshResult,
    ScheduleInput,
    SourceMode,
    SyllabusFileInput,
    SyllabusInput,
)
from easy_a.refresh.service import RefreshStageError, refresh_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh available Easy-A data sources for one explicit Banner term."
    )
    parser.add_argument("--term", required=True, type=_term_code)

    parser.add_argument("--catalog-source", choices=_SOURCE_CHOICES)
    parser.add_argument("--catalog-edition")
    parser.add_argument("--catalog-url")
    parser.add_argument("--catalog-file", type=Path)
    parser.add_argument("--skip-catalog", action="store_true")

    parser.add_argument("--schedule-source", choices=_SOURCE_CHOICES)
    parser.add_argument("--schedule-file", type=Path)
    parser.add_argument("--schedule-campus")
    parser.add_argument("--schedule-subject")
    parser.add_argument("--schedule-course")
    parser.add_argument("--schedule-crn")
    parser.add_argument("--skip-schedule", action="store_true")

    parser.add_argument("--grade-file", type=Path)
    parser.add_argument("--skip-grades", action="store_true")

    parser.add_argument("--syllabus-source", choices=_SOURCE_CHOICES)
    parser.add_argument(
        "--syllabus-document",
        action="append",
        help="Public Simple Syllabus document ID or URL; may be repeated.",
    )
    parser.add_argument(
        "--syllabus-file",
        action="append",
        type=_syllabus_file,
        metavar="DOCUMENT_ID=HTML",
        help="Local syllabus HTML with its explicit document ID; may be repeated.",
    )
    parser.add_argument("--skip-syllabi", action="store_true")

    parser.add_argument(
        "--stale-after-days",
        type=_nonnegative_int,
        default=DEFAULT_STALE_AFTER_DAYS,
    )
    return parser


def config_from_args(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> RefreshConfig:
    try:
        return RefreshConfig(
            term=args.term,
            catalog=_catalog_input(args),
            schedule=_schedule_input(args),
            grades=(
                None
                if args.skip_grades or args.grade_file is None
                else GradeInput(args.grade_file)
            ),
            syllabi=_syllabus_input(args),
            stale_after=timedelta(days=args.stale_after_days),
        )
    except RefreshConfigurationError as exc:
        parser.error(str(exc))


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    config = config_from_args(parser.parse_args(argv), parser)
    try:
        result = refresh_data(config)
    except RefreshStageError as exc:
        print(f"Refresh failed during {exc.stage}: {exc.cause}")
        return 2

    print(format_refresh_result(result))
    return 1 if result.quality_report.has_errors else 0


def format_refresh_result(result: RefreshResult) -> str:
    return "\n".join(
        [
            f"Term: {result.term}",
            f"Courses: {result.courses}",
            f"Sections: {result.sections}",
            f"Instructor observations added: {result.instructor_observations_added}",
            f"Seat snapshots added: {result.seat_snapshots_added}",
            f"Grade rows: {result.grade_rows}",
            f"Syllabi: {result.syllabi}",
            f"Quality errors: {result.quality_report.error_count}",
            f"Quality warnings: {result.quality_report.warning_count}",
        ]
    )


def _catalog_input(args: argparse.Namespace) -> CatalogInput | None:
    if args.skip_catalog:
        return None
    if args.catalog_source is None:
        if any(
            value is not None
            for value in (args.catalog_edition, args.catalog_url, args.catalog_file)
        ):
            raise RefreshConfigurationError(
                "Catalog options require --catalog-source live or file."
            )
        return None
    if args.catalog_edition is None:
        raise RefreshConfigurationError("Catalog refresh requires --catalog-edition.")
    return CatalogInput(
        source=SourceMode(args.catalog_source),
        catalog_edition=args.catalog_edition,
        url=args.catalog_url,
        file_path=args.catalog_file,
    )


def _schedule_input(args: argparse.Namespace) -> ScheduleInput | None:
    if args.skip_schedule:
        return None
    schedule_options = (
        args.schedule_file,
        args.schedule_campus,
        args.schedule_subject,
        args.schedule_course,
        args.schedule_crn,
    )
    if args.schedule_source is None:
        if any(value is not None for value in schedule_options):
            raise RefreshConfigurationError(
                "Schedule options require --schedule-source live or file."
            )
        return None
    return ScheduleInput(
        source=SourceMode(args.schedule_source),
        file_path=args.schedule_file,
        campus=args.schedule_campus,
        subject=args.schedule_subject,
        course=args.schedule_course,
        crn=args.schedule_crn,
    )


def _syllabus_input(args: argparse.Namespace) -> SyllabusInput | None:
    if args.skip_syllabi:
        return None
    documents = tuple(args.syllabus_document or ())
    files = tuple(args.syllabus_file or ())
    if args.syllabus_source is None:
        if documents or files:
            raise RefreshConfigurationError(
                "Syllabus options require --syllabus-source live or file."
            )
        return None
    return SyllabusInput(
        source=SourceMode(args.syllabus_source),
        documents=documents,
        files=files,
    )


def _syllabus_file(value: str) -> SyllabusFileInput:
    document_id, separator, raw_path = value.partition("=")
    if not separator or not document_id.strip() or not raw_path.strip():
        raise argparse.ArgumentTypeError("expected DOCUMENT_ID=HTML")
    try:
        return SyllabusFileInput(document_id=document_id, file_path=Path(raw_path))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _term_code(value: str) -> str:
    try:
        return normalize_banner_term_code(value)
    except TermParseError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _nonnegative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


_SOURCE_CHOICES = tuple(mode.value for mode in SourceMode)
