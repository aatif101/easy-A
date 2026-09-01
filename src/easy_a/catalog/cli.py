from __future__ import annotations

import argparse
from pathlib import Path

from easy_a.catalog.client import fetch_catalog_html
from easy_a.catalog.ingest import ingest_catalog_html
from easy_a.db import get_session_factory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest public USF catalog course HTML.")
    parser.add_argument("--catalog-edition", required=True, help="Catalog edition, e.g. 2026-2027.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Public catalog or course inventory URL to fetch.")
    source.add_argument("--file", type=Path, help="Local HTML fixture/file to ingest.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    html = (
        fetch_catalog_html(args.url)
        if args.url is not None
        else args.file.read_text(encoding="utf-8")
    )

    session_factory = get_session_factory()
    with session_factory() as session:
        try:
            result = ingest_catalog_html(
                session=session,
                html=html,
                catalog_edition=args.catalog_edition,
            )
        except Exception:
            session.commit()
            raise
        session.commit()

    print(
        "Catalog ingest succeeded: "
        f"seen={result.records_seen} "
        f"inserted={result.records_inserted} "
        f"updated={result.records_updated} "
        f"run_id={result.ingest_run_id}"
    )
    return 0
