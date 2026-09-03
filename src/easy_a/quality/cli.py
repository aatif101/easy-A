from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import timedelta

from sqlalchemy.orm import Session, sessionmaker

from easy_a.common.terms import TermParseError, normalize_banner_term_code
from easy_a.db import get_session_factory
from easy_a.quality.checks import DEFAULT_STALE_AFTER_DAYS, run_quality_checks
from easy_a.quality.models import FindingSeverity, QualityFinding, QualityReport


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check Easy-A data quality for one term.")
    parser.add_argument(
        "--term",
        required=True,
        type=_term_code,
        help="Six-digit Banner term, e.g. 202701.",
    )
    parser.add_argument(
        "--stale-after-days",
        type=_nonnegative_int,
        default=DEFAULT_STALE_AFTER_DAYS,
        help="Warn when the latest schedule observation is older than this many days.",
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
    with factory() as session:
        report = run_quality_checks(
            session,
            args.term,
            stale_after=timedelta(days=args.stale_after_days),
        )

    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        print(format_human_report(report))
    return 1 if report.has_errors else 0


def format_human_report(report: QualityReport) -> str:
    lines = [
        f"Term: {report.term}",
        f"Sections: {report.section_count}",
        f"Errors: {report.error_count}",
        f"Warnings: {report.warning_count}",
        f"Info: {report.info_count}",
    ]
    if report.findings:
        lines.append("")
        lines.extend(_format_finding(finding) for finding in report.findings)
    return "\n".join(lines)


def _format_finding(finding: QualityFinding) -> str:
    label = {
        FindingSeverity.error: "ERROR",
        FindingSeverity.warning: "WARN",
        FindingSeverity.info: "INFO",
    }[finding.severity]
    identity = f" CRN {finding.crn}" if finding.crn is not None else ""
    source = f" [{finding.source_record}]" if finding.source_record is not None else ""
    return f"{label} {finding.check_id}{identity}{source}: {finding.message}"


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
