from __future__ import annotations

import argparse
from collections.abc import Sequence

from sqlalchemy.orm import Session, sessionmaker

from easy_a.common.terms import TermParseError, normalize_banner_term_code
from easy_a.db import get_session_factory
from easy_a.refresh.cleanup import (
    TAMPA_CAMPUS,
    CleanupError,
    CleanupReport,
    SectionRef,
    StoredCounts,
    clean_other_campus_sections,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Remove stored sections in one term whose campus is not the supported campus. "
            "Reports without writing anything unless --apply is given."
        )
    )
    parser.add_argument(
        "--term",
        required=True,
        type=_term_code,
        help="Six-digit Banner term, e.g. 202701.",
    )
    parser.add_argument(
        "--keep-campus",
        default=TAMPA_CAMPUS,
        help=f"Campus label to keep; every other campus is removed. Default: {TAMPA_CAMPUS}.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the deletion. Without it the command only reports what it would remove.",
    )
    parser.add_argument(
        "--expect-removed",
        type=_nonnegative_int,
        help="Refuse to proceed unless exactly this many sections match the criteria.",
    )
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON.")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    factory = session_factory or get_session_factory()
    try:
        with factory.begin() as session:
            report = clean_other_campus_sections(
                session,
                term=args.term,
                kept_campus=args.keep_campus,
                apply=args.apply,
                expect_removed=args.expect_removed,
            )
    except CleanupError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(report.model_dump_json(indent=2) if args.json else format_human_report(report))
    return 0


def format_human_report(report: CleanupReport) -> str:
    lines = [
        f"Term: {report.term}",
        f"Keeping campus: {report.kept_campus}",
        f"Mode: {'APPLIED' if report.applied else 'dry run - nothing written'}",
        f"Criteria: {report.criteria}",
        "",
        "Stored before:",
        *_format_counts(report.before),
        "",
        f"Matched for removal: {len(report.matched)}",
        *(_format_match(ref) for ref in report.matched),
    ]
    if report.after is None:
        lines.append("")
        lines.append(
            f"Nothing to remove: no non-{report.kept_campus} sections are stored for "
            f"term {report.term}."
            if report.applied
            else "Nothing was deleted. Re-run with --apply to remove the matched sections."
        )
        return "\n".join(lines)

    lines.extend(
        [
            "",
            "Stored after:",
            *_format_counts(report.after),
            "",
            f"Sections removed: {report.sections_removed}",
            f"Seat snapshots removed: {report.seat_snapshots_removed}",
            f"Instructor observations removed: {report.instructor_observations_removed}",
            f"{report.kept_campus} sections removed: {report.kept_campus_sections_removed}",
            f"Grade rows removed: {report.grade_rows_removed}",
            "",
            f"Preserved: {report.after.kept_campus_sections} {report.kept_campus} sections and "
            f"{report.after.grade_rows_all_terms} grade rows across all terms.",
        ]
    )
    return "\n".join(lines)


def _format_counts(counts: StoredCounts) -> list[str]:
    lines = [f"  Sections: {counts.sections}"]
    lines.extend(f"    {row.campus}: {row.section_count}" for row in counts.by_campus)
    lines.extend(
        [
            f"  Seat snapshots: {counts.seat_snapshots}",
            f"  Instructor observations: {counts.instructor_observations}",
            f"  Syllabi: {counts.syllabi}",
            f"  Grade rows (this term): {counts.grade_rows_term}",
            f"  Grade rows (all terms): {counts.grade_rows_all_terms}",
        ]
    )
    return lines


def _format_match(ref: SectionRef) -> str:
    extra = (
        f"  grade-rows-on-term+CRN={ref.grade_rows_same_term_crn}"
        if ref.grade_rows_same_term_crn
        else ""
    )
    return (
        f"  CRN {ref.crn}  {ref.subject} {ref.course_number}-{ref.section_number}  "
        f"campus={ref.campus}  snapshots={ref.seat_snapshots}  "
        f"instructors={ref.instructor_observations}{extra}"
    )


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
