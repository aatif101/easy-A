from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.common.instructors import get_current_instructor_state
from easy_a.models import Section, Syllabus, Term
from easy_a.signals.extract import extract_signals
from easy_a.signals.models import ResolvedSignalSet, SignalSourceKind


class SignalResolutionError(ValueError):
    """Raised when the requested current section cannot be resolved uniquely."""


@dataclass(frozen=True)
class InstructorResolution:
    name: str | None
    confidence: float | None


def resolve_instructor(current_name: str, historical_names: list[str]) -> InstructorResolution:
    current = _name_parts(current_name)
    if current is None:
        return InstructorResolution(None, None)

    unique_candidates = {
        normalized: raw
        for raw in historical_names
        if (normalized := _normalize_name(raw)) and normalized != "staff"
    }
    current_normalized = _normalize_name(current_name)
    if current_normalized in unique_candidates:
        return InstructorResolution(unique_candidates[current_normalized], 1.0)

    abbreviation_matches: list[str] = []
    for candidate in unique_candidates.values():
        candidate_parts = _name_parts(candidate)
        if candidate_parts is None:
            continue
        current_first, current_surname = current
        candidate_first, candidate_surname = candidate_parts
        if (
            current_surname == candidate_surname
            and current_first[0] == candidate_first[0]
            and (len(current_first) == 1 or len(candidate_first) == 1)
        ):
            abbreviation_matches.append(candidate)
    if len(abbreviation_matches) == 1:
        return InstructorResolution(abbreviation_matches[0], 0.85)
    return InstructorResolution(None, None)


def resolve_section_signals(
    session: Session,
    *,
    term: str,
    crn: str,
) -> ResolvedSignalSet:
    section_row = session.execute(
        select(Section, Term)
        .join(Term, Section.term_id == Term.id)
        .where(Term.banner_code == term.strip(), Section.crn == crn.strip())
    ).one_or_none()
    if section_row is None:
        raise SignalResolutionError(f"No section found for term {term!r} and CRN {crn!r}.")
    section, current_term = section_row

    current_syllabus = session.execute(
        select(Syllabus)
        .where(Syllabus.term_id == current_term.id, Syllabus.crn == section.crn)
        .order_by(Syllabus.fetched_at.desc(), Syllabus.id.desc())
    ).scalars().first()
    if current_syllabus is not None:
        return _from_syllabus(
            section,
            current_syllabus,
            current_term.banner_code,
            SignalSourceKind.current_term_syllabus,
        )

    if section.section_note:
        note_signals = extract_signals(
            section.section_note,
            source_kind=SignalSourceKind.schedule_section_note,
            source_identifier=f"section:{section.id}:note",
            source_term=current_term.banner_code,
        )
        if note_signals:
            return ResolvedSignalSet(
                section_id=section.id,
                signals=note_signals,
                provenance=SignalSourceKind.schedule_section_note,
                source_term=current_term.banner_code,
                historical=False,
            )

    history = session.execute(
        select(Syllabus, Term)
        .join(Term, Syllabus.term_id == Term.id)
        .where(
            Syllabus.course_id == section.course_id,
            Term.banner_code < current_term.banner_code,
        )
        .order_by(Term.banner_code.desc(), Syllabus.fetched_at.desc(), Syllabus.id.desc())
    ).all()
    if history:
        current_instructor = get_current_instructor_state(session, section.id).name
        instructor_resolution = resolve_instructor(
            current_instructor or "",
            [syllabus.instructor_raw for syllabus, _ in history if syllabus.instructor_raw],
        )
        if instructor_resolution.name is not None:
            normalized_match = _normalize_name(instructor_resolution.name)
            for syllabus, source_term in history:
                if _normalize_name(syllabus.instructor_raw or "") == normalized_match:
                    return _from_syllabus(
                        section,
                        syllabus,
                        source_term.banner_code,
                        SignalSourceKind.historical_same_instructor_course,
                        instructor_match_confidence=instructor_resolution.confidence,
                    )

        syllabus, source_term = history[0]
        return _from_syllabus(
            section,
            syllabus,
            source_term.banner_code,
            SignalSourceKind.historical_same_course,
        )

    return ResolvedSignalSet(
        section_id=section.id,
        signals=(),
        provenance=SignalSourceKind.unavailable,
        source_term=None,
        historical=False,
    )


def _from_syllabus(
    section: Section,
    syllabus: Syllabus,
    source_term: str,
    source_kind: SignalSourceKind,
    *,
    instructor_match_confidence: float | None = None,
) -> ResolvedSignalSet:
    signals = extract_signals(
        syllabus.content_text,
        source_kind=source_kind,
        source_identifier=f"syllabus:{syllabus.document_id}",
        source_term=source_term,
    )
    historical = source_kind in {
        SignalSourceKind.historical_same_instructor_course,
        SignalSourceKind.historical_same_course,
    }
    return ResolvedSignalSet(
        section_id=section.id,
        signals=signals,
        provenance=source_kind,
        source_term=source_term,
        historical=historical,
        instructor_match_confidence=instructor_match_confidence,
    )
def _name_parts(name: str) -> tuple[str, str] | None:
    normalized = _normalize_name(name)
    if not normalized or normalized == "staff":
        return None
    parts = normalized.split()
    if len(parts) < 2:
        return None
    return parts[0], parts[-1]


def _normalize_name(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    if "," in ascii_name:
        surname, given = ascii_name.split(",", 1)
        ascii_name = f"{given} {surname}"
    return " ".join(re.findall(r"[a-z]+", ascii_name.lower()))
