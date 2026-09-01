from __future__ import annotations

import argparse

from easy_a.db import get_session_factory
from easy_a.syllabi.client import SimpleSyllabusClient
from easy_a.syllabi.ingest import ingest_syllabus_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest one public Simple Syllabus document.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--document-id")
    source.add_argument("--url")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    document = args.document_id or args.url
    with SimpleSyllabusClient() as client:
        document_id, html = client.fetch_document_html(document)

    session_factory = get_session_factory()
    with session_factory.begin() as session:
        result = ingest_syllabus_html(session, html, document_id=document_id)
    print(
        "Syllabus ingest succeeded: "
        f"id={result.syllabus_id} inserted={result.inserted} "
        f"content_changed={result.content_changed} "
        f"joined_to_section={result.joined_to_section}"
    )
    return 0
