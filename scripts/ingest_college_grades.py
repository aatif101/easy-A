"""Import a validated InfoCenter export for courses in a current Tampa term.

The XLSX stays outside the repository. Its SHA-256 is stored on each imported row.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import select

from easy_a.common.lookups import ensure_term
from easy_a.db import get_engine, get_session_factory
from easy_a.grades.ingest import GRADE_DISTRIBUTION_SOURCE, hash_file, upsert_grade_distributions
from easy_a.grades.parser import parse_grade_workbook
from easy_a.models import Course, IngestRun, Section, Term


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--term", required=True, help="Historical Banner term code")
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--expected-rows", required=True, type=int)
    parser.add_argument("--expected-total-grades", required=True, type=int)
    parser.add_argument("--current-term", default="202701")
    parser.add_argument("--write", action="store_true", help="Commit the validated import")
    args = parser.parse_args()

    records = parse_grade_workbook(args.file)
    if len(records) != args.expected_rows:
        raise SystemExit(f"Row count mismatch: {len(records)} != {args.expected_rows}")
    total = sum(record.total_grades for record in records)
    if total != args.expected_total_grades:
        raise SystemExit(f"Total grades mismatch: {total} != {args.expected_total_grades}")
    if len({record.crn for record in records}) != len(records):
        raise SystemExit("Duplicate CRNs in export")
    if any(record.campus_raw != "0001 - Tampa Campus" for record in records):
        raise SystemExit("Export includes a non-Tampa or unidentified campus row")

    database_url = dotenv_values(".env").get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL missing from .env")
    factory = get_session_factory(get_engine(database_url))
    with factory() as session:
        current_keys = set(
            session.execute(
                select(Course.subject, Course.number)
                .join(Section, Section.course_id == Course.id)
                .join(Term, Term.id == Section.term_id)
                .where(Term.banner_code == args.current_term, Section.campus.ilike("%Tampa%"))
                .distinct()
            ).all()
        )
        selected = [
            record for record in records if (record.subject, record.course_number) in current_keys
        ]
        print(
            f"Validated export: {len(records)} rows, {total} grades; "
            f"{len(selected)} rows and "
            f"{len({(r.subject, r.course_number) for r in selected})} "
            "current Tampa courses selected"
        )
        if not args.write:
            return
        if not selected:
            raise SystemExit("No current Tampa courses in export")

        try:
            term = ensure_term(session, args.term)
            run = IngestRun(
                source=GRADE_DISTRIBUTION_SOURCE,
                status="running",
                records_seen=len(records),
                records_inserted=0,
                records_updated=0,
                records_failed=0,
            )
            session.add(run)
            session.flush()
            inserted, updated = upsert_grade_distributions(
                session=session,
                term=term,
                records=selected,
                source=GRADE_DISTRIBUTION_SOURCE,
                source_hash=hash_file(args.file),
            )
            run.status = "succeeded"
            run.finished_at = datetime.now(UTC)
            run.records_inserted = inserted
            run.records_updated = updated
            session.commit()
        except Exception:
            session.rollback()
            raise
        print(f"Committed: inserted={inserted}, updated={updated}, run_id={run.id}")


if __name__ == "__main__":
    main()
