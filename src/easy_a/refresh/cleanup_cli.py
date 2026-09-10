from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from easy_a.common.terms import TermParseError, normalize_banner_term_code
from easy_a.db import get_session_factory
from easy_a.refresh.cleanup import (
    CleanupError,
    CleanupReport,
    SectionRef,
    StoredCounts,
    clean_other_campus_sections,
)
from easy_a.refresh.targets import load_targets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Report or remove non-Tampa sections for configured beta targets in one term. "
            "Dry-run is the default. Stop schedule/seat writers before using --apply."
        )
    )
    parser.add_argument("--term", required=True, type=_term_code, help="Six-digit Banner term.")
    parser.add_argument(
        "--targets",
        type=Path,
        help="Course-target TOML path. Defaults to EASY_A_COURSE_TARGETS_PATH/config default.",
    )
    parser.add_argument("--apply", action="store_true", help="Commit the reviewed deletion.")
    parser.add_argument(
        "--expect-removed",
        type=_nonnegative_int,
        help="Required with --apply; abort unless exactly this many sections are eligible.",
    )
    parser.add_argument("--json", action="store_true", help="Print the full audit report as JSON.")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.apply and args.expect_removed is None:
        parser.error("--apply requires --expect-removed")

    try:
        config = load_targets(args.targets)
        factory = session_factory or get_session_factory()
        with factory.begin() as session:
            report = clean_other_campus_sections(
                session,
                term=args.term,
                targets=config.targets,
                apply=args.apply,
                expect_removed=args.expect_removed,
            )
    except (CleanupError, OSError, SQLAlchemyError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(report.model_dump_json(indent=2) if args.json else format_human_report(report))
    return 0


def format_human_report(report: CleanupReport) -> str:
    lines = [
        f"Term: {report.term}",
        f"Configured targets: {', '.join(report.targets)}",
        f"Keeping campus: {report.kept_campus}",
        f"Mode: {'APPLIED' if report.applied else 'DRY RUN - NOTHING WRITTEN'}",
        f"Apply safety check: {'PASS' if report.apply_safe else 'BLOCKED BY GRADE ROWS'}",
        f"Criteria: {report.criteria}",
        "",
        "Stored before:",
        *_format_counts(report.before),
        "",
        f"Eligible for removal: {len(report.matched)}",
        f"Candidate seat snapshots: {report.candidate_seat_snapshots}",
        f"Candidate instructor observations: {report.candidate_instructor_observations}",
        f"Candidate syllabi: {report.candidate_syllabi}",
        f"Candidate grade rows: {report.candidate_grade_rows} (must be 0 to apply)",
        *(_format_ref(ref) for ref in report.matched),
        f"Ambiguous campus (never auto-deleted): {len(report.ambiguous)}",
        *(_format_ref(ref) for ref in report.ambiguous),
    ]
    if report.after is None:
        lines.extend(["", "Nothing was deleted."])
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
            f"Syllabi removed: {report.syllabi_removed}",
            f"Grade rows removed: {report.grade_rows_removed}",
            f"Tampa sections removed: {report.tampa_sections_removed}",
            f"Ambiguous sections removed: {report.ambiguous_sections_removed}",
            f"Historical sections removed: {report.historical_sections_removed}",
            f"Unrelated current-term sections removed: {report.unrelated_term_sections_removed}",
        ]
    )
    return "\n".join(lines)


def _format_counts(counts: StoredCounts) -> list[str]:
    lines = [
        f"  All sections in term: {counts.term_sections}",
        f"  Configured-target sections: {counts.target_sections}",
        f"  Tampa target sections: {counts.tampa_target_sections}",
        f"  Other-campus target sections: {counts.other_campus_target_sections}",
        f"  Ambiguous-campus target sections: {counts.ambiguous_target_sections}",
        f"  Unrelated sections in term: {counts.unrelated_term_sections}",
        f"  Historical-term sections: {counts.historical_sections}",
        f"  Target seat snapshots: {counts.target_seat_snapshots}",
        f"  Target instructor observations: {counts.target_instructor_observations}",
        f"  Target syllabi: {counts.target_syllabi}",
        f"  Grade rows (term): {counts.grade_rows_term}",
        f"  Grade rows (all terms): {counts.grade_rows_all_terms}",
    ]
    lines.extend(f"    campus {row.campus}: {row.section_count}" for row in counts.by_campus)
    lines.extend(
        f"    {row.subject} {row.course_number}: total={row.sections}, "
        f"Tampa={row.tampa_sections}, other={row.other_campus_sections}, "
        f"ambiguous={row.ambiguous_campus_sections}"
        for row in counts.by_course
    )
    return lines


def _format_ref(ref: SectionRef) -> str:
    return (
        f"  id={ref.section_id} CRN={ref.crn} {ref.subject} {ref.course_number}-"
        f"{ref.section_number} campus={ref.campus!r} snapshots={ref.seat_snapshots} "
        f"instructors={ref.instructor_observations} syllabi={ref.syllabi} "
        f"same-term+CRN-grades={ref.grade_rows_same_term_crn}"
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
