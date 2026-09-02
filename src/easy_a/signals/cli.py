from __future__ import annotations

import argparse

from sqlalchemy import select

from easy_a.db import get_session_factory
from easy_a.models import Course, Section, SectionInstructor, Term
from easy_a.signals.models import ResolvedSignalSet
from easy_a.signals.resolver import SignalResolutionError, resolve_section_signals


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract deterministic policy signals for one stored section."
    )
    parser.add_argument("--term", required=True, help="Six-digit Banner term, e.g. 202701.")
    parser.add_argument("--crn", required=True, help="Term-scoped course reference number.")
    return parser


def format_signal_output(
    *,
    crn: str,
    course: str,
    instructor: str,
    result: ResolvedSignalSet,
) -> str:
    header = [f"CRN: {crn}", f"Course: {course}", f"Instructor: {instructor}"]
    if not result.signals:
        return "\n".join(
            [
                *header,
                "Signal: unknown",
                "Value: unknown",
                "Confidence: n/a",
                f"Source: {result.provenance.value}",
                f"Source term: {result.source_term or 'n/a'}",
                f"Historical/current: {'historical' if result.historical else 'current'}",
                "Evidence: n/a",
            ]
        )

    blocks: list[str] = []
    for signal in result.signals:
        blocks.append(
            "\n".join(
                [
                    f"Signal: {signal.signal_type.value}",
                    f"Value: {signal.value}",
                    f"Confidence: {signal.confidence:.2f}",
                    f"Source: {signal.source_kind.value} ({signal.source_identifier})",
                    f"Source term: {signal.source_term}",
                    f"Historical/current: {'historical' if result.historical else 'current'}",
                    f"Evidence: {signal.evidence_text}",
                ]
            )
        )
    return "\n".join([*header, "", "\n\n".join(blocks)])


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    session_factory = get_session_factory()
    with session_factory() as session:
        section_row = session.execute(
            select(Section, Course)
            .join(Term, Section.term_id == Term.id)
            .join(Course, Section.course_id == Course.id)
            .where(Term.banner_code == args.term.strip(), Section.crn == args.crn.strip())
        ).one_or_none()
        if section_row is None:
            raise SignalResolutionError(
                f"No section found for term {args.term!r} and CRN {args.crn!r}."
            )
        section, course = section_row
        instructor_names = session.scalars(
            select(SectionInstructor.name_raw)
            .where(SectionInstructor.section_id == section.id)
            .distinct()
        ).all()
        result = resolve_section_signals(session, term=args.term, crn=args.crn)

    print(
        format_signal_output(
            crn=section.crn,
            course=f"{course.subject} {course.number} - {course.title}",
            instructor=" / ".join(instructor_names) or "Unknown",
            result=result,
        )
    )
    return 0
