from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

import scripts.inventory_tampa_grades as inv
from easy_a.models import Course, GradeDistribution, Section
from easy_a.rankings.cache import refresh_section_rankings

TERM = "202701"


def _add_course(session: Session, *, course_id: int, subject: str, number: str) -> Course:
    course = Course(
        id=course_id,
        subject=subject,
        number=number,
        title=f"{subject} {number}",
        catalog_edition="2026-2027",
    )
    session.add(course)
    session.flush()
    return course


def _add_section(session: Session, *, course_id: int, crn: str, term_id: int = 1) -> Section:
    from datetime import UTC, datetime

    now = datetime(2026, 9, 22, 12, tzinfo=UTC)
    section = Section(
        term_id=term_id,
        crn=crn,
        course_id=course_id,
        section_number="001",
        campus="Tampa",
        session="Full Semester",
        section_type="Lecture",
        primary_status="A",
        first_seen_at=now,
        last_seen_at=now,
    )
    session.add(section)
    session.flush()
    return section


def _add_grade(
    session: Session,
    *,
    term_id: int,
    crn: str,
    course_id: int,
    a: int = 0,
    b: int = 0,
    c: int = 0,
    d: int = 0,
    f: int = 0,
    s: int = 0,
    u: int = 0,
    w: int = 0,
    source: str = "synthetic",
) -> GradeDistribution:
    completed = a + b + c + d + f
    total = completed + s + u + w
    distribution = GradeDistribution(
        term_id=term_id,
        crn=crn,
        course_id=course_id,
        section_number_raw="001",
        section_suffix_raw=None,
        campus_raw="Tampa",
        a_count=a,
        b_count=b,
        c_count=c,
        d_count=d,
        f_count=f,
        i_count=0,
        s_count=s,
        u_count=u,
        w_count=w,
        other_count=0,
        total_grades=total,
        source=source,
        source_hash=f"{source}-hash",
    )
    session.add(distribution)
    session.flush()
    return distribution


def _seed_evidence_backed_and_exception_no_rows(session: Session) -> None:
    """MAC 1105 (id=10, conftest) gets 2 historical letter-grade rows and a current
    section: it should classify evidence_backed. MAC 2311 (a second course, same
    subject, no rows of its own) gets a current section only: its subject-level
    fallback picks up MAC 1105's rows, so it should classify exception_no_rows."""
    _add_grade(session, term_id=2, crn="80001", course_id=10, a=10, source="synthetic-1")
    _add_grade(session, term_id=2, crn="80002", course_id=10, a=5, source="synthetic-2")
    _add_section(session, course_id=10, crn="90001")

    _add_course(session, course_id=20, subject="MAC", number="2311")
    _add_section(session, course_id=20, crn="90002")

    session.commit()
    refreshed = refresh_section_rankings(session, term=TERM)
    session.commit()
    assert refreshed == 2


def test_evidence_backed_section_traced_through_cache(db_session: Session) -> None:
    _seed_evidence_backed_and_exception_no_rows(db_session)

    inventory = inv.collect_inventory(db_session, TERM)
    by_crn = {s.crn: s for s in inventory.sections}

    result = by_crn["90001"]
    assert result.state == inv.EvidenceState.evidence_backed
    assert result.score_source == "course"
    assert result.effective_n is not None and result.effective_n > 0
    assert result.row_count == 2
    assert result.total_grades_sum == 15
    assert set(result.historical_term_codes) == {"202408"}
    assert set(result.sources) == {"synthetic-1", "synthetic-2"}
    assert result.cached_total_grade_count == result.total_grades_sum


def test_exception_no_rows_section_uses_subject_fallback(db_session: Session) -> None:
    _seed_evidence_backed_and_exception_no_rows(db_session)

    inventory = inv.collect_inventory(db_session, TERM)
    by_crn = {s.crn: s for s in inventory.sections}

    result = by_crn["90002"]
    assert result.state == inv.EvidenceState.exception_no_rows
    assert result.reason_category == "no_rows"
    assert result.reason_note == inv.NO_ROWS_REASON_NOTE
    assert result.score_source == "subject"
    assert result.effective_n is not None and result.effective_n > 0
    assert result.row_count == 0


def test_main_prints_snapshot_json_and_exits_nonzero_when_unclassified_present(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_evidence_backed_and_exception_no_rows(db_session)
    # A third, un-cached section: exercises the missing_cache_row -> FAIL path so
    # this Task-1 stub run legitimately exits 1 without needing full classification.
    _add_course(db_session, course_id=30, subject="ZZZ", number="1000")
    _add_section(db_session, course_id=30, crn="90003")
    db_session.commit()

    engine = db_session.get_bind()
    monkeypatch.setattr(inv, "get_engine", lambda: engine)
    monkeypatch.setattr(engine, "dispose", lambda: None)

    exit_code = inv.main(["--term", TERM])
    assert exit_code == 1

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["gate"] == "d21_grade_coverage"
    assert payload["snapshot"]["section_count"] == 3

    forbidden_keys = {
        "a_count",
        "b_count",
        "c_count",
        "d_count",
        "f_count",
        "s_count",
        "u_count",
        "w_count",
    }
    assert forbidden_keys.isdisjoint(_all_keys(payload))


def _all_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, val in value.items():
            keys.add(key)
            keys |= _all_keys(val)
    elif isinstance(value, list):
        for item in value:
            keys |= _all_keys(item)
    return keys


def test_classify_section_missing_cache_row() -> None:
    result = inv.classify_section(
        crn="99999",
        subject="ZZZ",
        course_number="1000",
        cache_row=None,
        key_evidence=inv.CourseKeyEvidence(),
    )
    assert result.state == inv.EvidenceState.missing_cache_row
    assert result.score_source is None


def test_write_atomic_leaves_target_absent_on_simulated_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "out.md"

    def failing_replace(*args: object, **kwargs: object) -> None:
        raise OSError("simulated failure")

    monkeypatch.setattr(inv.os, "replace", failing_replace)
    with pytest.raises(OSError, match="simulated failure"):
        inv.write_atomic(target, "content")
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []
