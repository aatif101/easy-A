from __future__ import annotations

from easy_a.analytics.cli import build_parser


def test_analyze_course_cli_requires_term_subject_and_course() -> None:
    parser = build_parser()

    assert (
        parser.parse_args(["--term", "202701", "--subject", "MAC", "--course", "1105"]).course
        == "1105"
    )
