from __future__ import annotations

import argparse
from pathlib import Path

from easy_a.db import get_session_factory
from easy_a.grades.ingest import GRADE_DISTRIBUTION_SOURCE, ingest_grade_file
from easy_a.grades.parser import GradeWorkbookSchemaError, GradeWorkbookValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest a local USF InfoCenter grade XLSX export.")
    parser.add_argument("--term", required=True, help="Required Banner term code, e.g. 202408.")
    parser.add_argument("--file", required=True, type=Path, help="Path to the local XLSX export.")
    parser.add_argument("--source", default=GRADE_DISTRIBUTION_SOURCE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    session_factory = get_session_factory()

    with session_factory() as session:
        try:
            result = ingest_grade_file(
                session=session,
                term_code=args.term,
                file_path=args.file,
                source=args.source,
            )
        except (GradeWorkbookSchemaError, GradeWorkbookValidationError) as exc:
            session.commit()
            print(f"Grade ingest failed: {exc}")
            return 1
        except Exception:
            session.commit()
            raise
        session.commit()

    print(
        "Grade ingest succeeded: "
        f"seen={result.records_seen} "
        f"inserted={result.records_inserted} "
        f"updated={result.records_updated} "
        f"run_id={result.ingest_run_id}"
    )
    return 0
