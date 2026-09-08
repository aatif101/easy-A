from __future__ import annotations

import argparse
from pathlib import Path

from easy_a.common.lookups import ensure_term
from easy_a.db import get_session_factory
from easy_a.quality.checks import run_quality_checks
from easy_a.quality.models import FindingSeverity, QualityFinding, QualityReport
from easy_a.refresh.coverage import refresh_targets
from easy_a.refresh.targets import load_targets
from easy_a.schedule.client import StaffScheduleClient


def main(argv: list[str] | None = None, *, coverage: bool = False) -> int:
    parser = argparse.ArgumentParser(description="One-pass configured course refresh")
    parser.add_argument("--term", required=True)
    parser.add_argument("--targets", type=Path)
    parser.add_argument("--subject")
    parser.add_argument("--course")
    parser.add_argument("--crn")
    args = parser.parse_args(argv)
    config = load_targets(args.targets)
    targets = config.select(args.subject, args.course)
    with get_session_factory().begin() as session, StaffScheduleClient() as client:
        ensure_term(session, args.term)
        rows = refresh_targets(
            session,
            term=args.term,
            config=config,
            search=client.search,
            refresh_catalog=coverage,
            subject=args.subject,
            course=args.course,
            crn=args.crn,
        )
        report = run_quality_checks(session, args.term, targets=targets)
        findings = list(report.findings)
        for row in rows:
            if not row.catalog_present or row.section_count == 0:
                findings.append(
                    QualityFinding(
                        check_id="target_missing_refresh",
                        severity=FindingSeverity.warning,
                        term=args.term,
                        source_record=f"{row.subject} {row.course_number}",
                        message="Configured target had no usable catalog/sections in this pass.",
                    )
                )
        report = QualityReport.from_findings(
            term=report.term,
            generated_at=report.generated_at,
            section_count=report.section_count,
            findings=findings,
        )
    print(f"Term: {args.term}")
    for row in rows:
        print(
            f"\n{row.subject} {row.course_number}\nSections: {row.section_count}\n"
            f"Catalog: {'ok' if row.catalog_present else 'missing'}\n"
            f"Schedule: {'ok' if row.section_count else 'missing'}\n"
            f"Seat snapshots added: {row.snapshots_added}"
        )
    missing = sum(not r.catalog_present or not r.section_count for r in rows)
    print(
        f"\nMissing targets: {missing}\nQuality errors: {report.error_count}\n"
        f"Quality warnings: {report.warning_count}"
    )
    for finding in report.findings:
        print(f"{finding.severity}: {finding.check_id}: {finding.message}")
    return 1 if report.has_errors else 0
