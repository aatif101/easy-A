from __future__ import annotations

from datetime import UTC, datetime

from easy_a.signals import ResolvedSignalSet, Signal, SignalSourceKind, SignalType
from easy_a.signals.cli import format_signal_output


def test_cli_output_labels_historical_provenance() -> None:
    result = ResolvedSignalSet(
        section_id=100,
        signals=(
            Signal(
                signal_type=SignalType.attendance,
                value="required",
                confidence=0.98,
                source_kind=SignalSourceKind.historical_same_instructor_course,
                source_identifier="syllabus:old",
                source_term="202408",
                evidence_text="Attendance is required.",
                extracted_at=datetime(2026, 9, 1, tzinfo=UTC),
            ),
        ),
        provenance=SignalSourceKind.historical_same_instructor_course,
        source_term="202408",
        historical=True,
        instructor_match_confidence=1.0,
    )

    output = format_signal_output(
        crn="19410",
        course="MAC 1105 - College Algebra",
        instructor="Leslaw Skrzypek",
        result=result,
    )

    assert "CRN: 19410" in output
    assert "Signal: attendance" in output
    assert "Source term: 202408" in output
    assert "Historical/current: historical" in output
    assert "Evidence: Attendance is required." in output
