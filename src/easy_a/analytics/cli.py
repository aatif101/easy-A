from __future__ import annotations

import argparse

from easy_a.analytics.queries import get_current_section_historical_analytics
from easy_a.db import get_session_factory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze historical outcomes for current sections."
    )
    parser.add_argument("--term", required=True, help="Current Banner term code, e.g. 202701.")
    parser.add_argument("--subject", required=True, help="Course subject, e.g. MAC.")
    parser.add_argument("--course", required=True, help="Course number, e.g. 1105.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    session_factory = get_session_factory()
    with session_factory() as session:
        rows = get_current_section_historical_analytics(
            session,
            term_code=args.term,
            subject=args.subject,
            course_number=args.course,
        )

    if not rows:
        print("No current sections found for the requested term and course.")
        return 0

    print(
        "CRN\tInstructor\tHistorical Easiness\tHistorical W Rate\tConfidence\tEffective N\tSource"
    )
    for row in rows:
        print(
            "\t".join(
                [
                    row.crn,
                    row.instructor or "Unassigned",
                    f"{row.historical_easiness:.2f}",
                    f"{row.historical_withdrawal_rate:.1%}",
                    row.stats.confidence_label.value,
                    f"{row.stats.effective_n:.1f}",
                    row.stats.score_source.value,
                ]
            )
        )
    return 0
