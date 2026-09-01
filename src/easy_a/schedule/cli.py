from __future__ import annotations

import argparse

from easy_a.db import get_session_factory
from easy_a.schedule.client import ScheduleSearchQuery, StaffScheduleClient
from easy_a.schedule.ingest import ingest_schedule_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest a narrow public USF schedule search.")
    parser.add_argument("--term", required=True, help="Six-digit Banner term, e.g. 202701.")
    parser.add_argument("--campus", help="Banner campus code, e.g. T for Tampa.")
    parser.add_argument("--subject", required=True, help="Course subject, e.g. MAC.")
    parser.add_argument("--course", help="Course number, e.g. 1105.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    query = ScheduleSearchQuery(
        term=args.term,
        campus=args.campus,
        subject=args.subject,
        course=args.course,
    )
    with StaffScheduleClient() as client:
        html = client.search(query)

    session_factory = get_session_factory()
    with session_factory.begin() as session:
        result = ingest_schedule_html(session, html, args.term)

    print(
        "Schedule ingest succeeded: "
        f"seen={result.records_seen} "
        f"inserted={result.records_inserted} "
        f"updated={result.records_updated} "
        f"snapshots={result.seat_snapshots_created} "
        f"instructor_observations={result.instructor_observations_created}"
    )
    return 0
