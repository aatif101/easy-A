from __future__ import annotations

import re
from datetime import UTC, datetime

from easy_a.signals.models import Signal, SignalSourceKind, SignalType
from easy_a.signals.provenance import evidence_window
from easy_a.signals.rules import RULES, SignalRule


def extract_signals(
    text: str,
    *,
    source_kind: SignalSourceKind,
    source_identifier: str,
    source_term: str,
    extracted_at: datetime | None = None,
) -> tuple[Signal, ...]:
    captured_at = extracted_at or datetime.now(UTC)
    candidates: dict[SignalType, list[tuple[SignalRule, re.Match[str]]]] = {}
    for rule in RULES:
        match = re.search(rule.pattern, text, flags=re.IGNORECASE)
        if match is None:
            continue
        candidates.setdefault(rule.signal_type, []).append((rule, match))

    signals: list[Signal] = []
    for signal_type, type_candidates in candidates.items():
        rule, match = type_candidates[0]
        value = rule.value
        confidence = rule.confidence
        evidence_start = match.start()
        evidence_end = match.end()
        if signal_type is SignalType.exam_location:
            location_values = {candidate_rule.value for candidate_rule, _ in type_candidates}
            if {"online", "in_person"}.issubset(location_values):
                value = "mixed"
                confidence = min(candidate_rule.confidence for candidate_rule, _ in type_candidates)
                evidence_start = min(
                    candidate_match.start() for _, candidate_match in type_candidates
                )
                evidence_end = max(candidate_match.end() for _, candidate_match in type_candidates)
        signals.append(Signal(
            signal_type=signal_type,
            value=value,
            confidence=confidence,
            source_kind=source_kind,
            source_identifier=source_identifier,
            source_term=source_term,
            evidence_text=evidence_window(text, evidence_start, evidence_end),
            extracted_at=captured_at,
        ))
    return tuple(signals)
