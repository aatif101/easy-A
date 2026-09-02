from __future__ import annotations

import argparse
import json

from easy_a.db import get_session_factory
from easy_a.rankings.models import SectionRanking
from easy_a.rankings.service import rank_course_sections, rank_section


def build_section_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank one stored section by term and CRN.")
    parser.add_argument("--term", required=True, help="Six-digit Banner term, e.g. 202701.")
    parser.add_argument("--crn", required=True, help="Term-scoped course reference number.")
    return parser


def build_course_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rank all stored sections for one course in a term."
    )
    parser.add_argument("--term", required=True, help="Six-digit Banner term, e.g. 202701.")
    parser.add_argument("--subject", required=True, help="Course subject, e.g. MAC.")
    parser.add_argument("--course", required=True, help="Course number, e.g. 1105.")
    return parser


def format_section_ranking(ranking: SectionRanking) -> str:
    return json.dumps(ranking.model_dump(mode="json"), indent=2)


def format_course_rankings(rankings: list[SectionRanking]) -> str:
    return json.dumps([ranking.model_dump(mode="json") for ranking in rankings], indent=2)


def section_main(argv: list[str] | None = None) -> int:
    args = build_section_parser().parse_args(argv)
    session_factory = get_session_factory()
    with session_factory() as session:
        ranking = rank_section(session, term=args.term, crn=args.crn)
    print(format_section_ranking(ranking))
    return 0


def course_main(argv: list[str] | None = None) -> int:
    args = build_course_parser().parse_args(argv)
    session_factory = get_session_factory()
    with session_factory() as session:
        rankings = rank_course_sections(
            session,
            term=args.term,
            subject=args.subject,
            course_number=args.course,
        )
    print(format_course_rankings(rankings))
    return 0
