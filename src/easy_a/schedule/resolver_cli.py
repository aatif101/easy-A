from __future__ import annotations

import argparse

from easy_a.schedule.client import ScheduleSearchQuery, StaffScheduleClient
from easy_a.schedule.resolver import ResolutionOutcome, resolve_historical_section


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve one historical USF section by term + CRN."
    )
    parser.add_argument("--term", required=True)
    parser.add_argument("--crn", required=True)
    parser.add_argument("--subject")
    parser.add_argument("--course")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    query = ScheduleSearchQuery(term=args.term, crn=args.crn)
    with StaffScheduleClient() as client:
        html = client.search(query)
    result = resolve_historical_section(
        html,
        crn=args.crn,
        expected_subject=args.subject,
        expected_course=args.course,
    )
    print(f"outcome={result.outcome.value}")
    if result.section is not None:
        section = result.section
        print(
            f"term={args.term} crn={section.crn} course={section.subject} "
            f"{section.course_number} section={section.section_number} "
            f"instructor={section.instructor_raw!r} campus={section.campus!r} "
            f"delivery_method={section.delivery_method!r} "
            f"status={section.primary_status!r} status2={section.secondary_status!r}"
        )
    elif result.reason is not None:
        print(result.reason)
    return 2 if result.outcome is ResolutionOutcome.ambiguous else 0
