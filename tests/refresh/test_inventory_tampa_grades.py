from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

import scripts.inventory_tampa_grades as inv
from easy_a.models import Course, GradeDistribution, Section, SectionRankingCache
from easy_a.rankings.cache import refresh_section_rankings

TERM = "202701"
NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)


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
    now = NOW
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


# --- Task 2: full classification decision tree -------------------------------------


def _stub_cache_row(
    *, score_source: str, effective_n: float, total_grade_count: int | None
) -> SectionRankingCache:
    row = SectionRankingCache()
    row.score_source = score_source
    row.effective_n = effective_n
    row.historical_analytics = (
        {"total_grade_count": total_grade_count} if total_grade_count is not None else {}
    )
    return row


def _key_evidence(
    *, row_count: int = 0, af_sum: int = 0, total_sum: int = 0, terms: tuple[str, ...] = ()
) -> inv.CourseKeyEvidence:
    return inv.CourseKeyEvidence(
        row_count=row_count,
        af_sum=af_sum,
        total_sum=total_sum,
        term_codes=frozenset(terms),
        sources=frozenset({"synthetic"}) if row_count else frozenset(),
    )


def test_classify_section_exception_non_letter_grade_when_reconciled() -> None:
    result = inv.classify_section(
        crn="10001",
        subject="ABC",
        course_number="4901",
        cache_row=_stub_cache_row(score_source="course", effective_n=0, total_grade_count=20),
        key_evidence=_key_evidence(row_count=1, af_sum=0, total_sum=20),
    )
    assert result.state == inv.EvidenceState.exception_non_letter_grade
    assert result.reason_category == "non_letter_grade"
    assert result.reason_note == inv.NON_LETTER_GRADE_REASON_NOTE


def test_classify_section_exception_non_letter_grade_mismatch_is_raw_total_mismatch() -> None:
    result = inv.classify_section(
        crn="10002",
        subject="ABC",
        course_number="4901",
        cache_row=_stub_cache_row(score_source="course", effective_n=0, total_grade_count=99),
        key_evidence=_key_evidence(row_count=1, af_sum=0, total_sum=20),
    )
    assert result.state == inv.EvidenceState.raw_total_mismatch
    assert result.reason_category is None


def test_classify_section_unbacked_course_claim_when_no_rows() -> None:
    result = inv.classify_section(
        crn="10003",
        subject="ABC",
        course_number="1000",
        cache_row=_stub_cache_row(score_source="course", effective_n=50.0, total_grade_count=100),
        key_evidence=_key_evidence(),
    )
    assert result.state == inv.EvidenceState.unbacked_course_claim


def test_classify_section_instructor_course_unbacked_when_no_rows() -> None:
    result = inv.classify_section(
        crn="10004",
        subject="ABC",
        course_number="1000",
        cache_row=_stub_cache_row(
            score_source="instructor_course", effective_n=0.0, total_grade_count=None
        ),
        key_evidence=_key_evidence(),
    )
    assert result.state == inv.EvidenceState.unbacked_course_claim


def test_classify_section_raw_total_mismatch_when_cached_total_disagrees() -> None:
    result = inv.classify_section(
        crn="10005",
        subject="ABC",
        course_number="1000",
        cache_row=_stub_cache_row(score_source="course", effective_n=50.0, total_grade_count=999),
        key_evidence=_key_evidence(row_count=2, af_sum=30, total_sum=100),
    )
    assert result.state == inv.EvidenceState.raw_total_mismatch


def test_classify_section_instructor_course_evidence_backed_subset_of_key_total() -> None:
    result = inv.classify_section(
        crn="10006",
        subject="ABC",
        course_number="1000",
        cache_row=_stub_cache_row(
            score_source="instructor_course", effective_n=20.0, total_grade_count=40
        ),
        key_evidence=_key_evidence(row_count=3, af_sum=90, total_sum=100),
    )
    assert result.state == inv.EvidenceState.evidence_backed


def test_classify_section_history_not_used_for_subject_when_key_has_rows() -> None:
    result = inv.classify_section(
        crn="10007",
        subject="ABC",
        course_number="1000",
        cache_row=_stub_cache_row(score_source="subject", effective_n=50.0, total_grade_count=None),
        key_evidence=_key_evidence(row_count=1, af_sum=10, total_sum=10),
    )
    assert result.state == inv.EvidenceState.history_not_used


def test_classify_section_history_not_used_for_global_when_key_has_rows() -> None:
    result = inv.classify_section(
        crn="10008",
        subject="ABC",
        course_number="1000",
        cache_row=_stub_cache_row(score_source="global", effective_n=0.0, total_grade_count=None),
        key_evidence=_key_evidence(row_count=1, af_sum=10, total_sum=10),
    )
    assert result.state == inv.EvidenceState.history_not_used


def test_classify_section_global_nonzero_effective_n() -> None:
    result = inv.classify_section(
        crn="10009",
        subject="ABC",
        course_number="1000",
        cache_row=_stub_cache_row(score_source="global", effective_n=10.0, total_grade_count=None),
        key_evidence=_key_evidence(),
    )
    assert result.state == inv.EvidenceState.global_nonzero_effective_n


def test_classify_section_unclassified_for_unknown_score_source() -> None:
    result = inv.classify_section(
        crn="10010",
        subject="ABC",
        course_number="1000",
        cache_row=_stub_cache_row(score_source="bogus", effective_n=0.0, total_grade_count=None),
        key_evidence=_key_evidence(),
    )
    assert result.state == inv.EvidenceState.unclassified


def test_classify_section_unclassified_for_subject_with_effective_n_zero() -> None:
    result = inv.classify_section(
        crn="10011",
        subject="ABC",
        course_number="1000",
        cache_row=_stub_cache_row(score_source="subject", effective_n=0.0, total_grade_count=None),
        key_evidence=_key_evidence(),
    )
    assert result.state == inv.EvidenceState.unclassified


def test_no_rows_reason_note_identical_across_every_no_rows_exception() -> None:
    subject_result = inv.classify_section(
        crn="20001",
        subject="ABC",
        course_number="1000",
        cache_row=_stub_cache_row(score_source="subject", effective_n=50.0, total_grade_count=None),
        key_evidence=_key_evidence(),
    )
    global_result = inv.classify_section(
        crn="20002",
        subject="XYZ",
        course_number="2000",
        cache_row=_stub_cache_row(score_source="global", effective_n=0.0, total_grade_count=None),
        key_evidence=_key_evidence(),
    )
    assert subject_result.state == inv.EvidenceState.exception_no_rows
    assert global_result.state == inv.EvidenceState.exception_no_rows
    assert subject_result.reason_note == global_result.reason_note == inv.NO_ROWS_REASON_NOTE


def _make_inventory(sections: tuple[inv.SectionState, ...]) -> inv.Inventory:
    return inv.Inventory(
        term=TERM,
        observed_at_utc="2026-09-24T00:00:00+00:00",
        environment="SQLite",
        sections=sections,
        represented_course_count=len({(s.subject, s.course_number) for s in sections}),
        cache_row_count=len(sections),
        cache_refreshed_at_min=None,
        cache_refreshed_at_max=None,
        grade_row_count=0,
        grade_ingested_at_max=None,
        non_tampa_section_count=0,
        grade_rows_by_term=(),
        window={"window_terms": {}, "checked_empty_terms": {}, "outside_window_rows": 0},
        unattributed_grade_rows=0,
        bucket_sum_mismatch_rows=0,
        rows_at_or_after_term=0,
        stale_cache=False,
    )


def test_d21_grade_coverage_pass_when_only_evidence_backed_and_exceptions() -> None:
    evidence_backed = inv.classify_section(
        crn="30001",
        subject="ABC",
        course_number="1000",
        cache_row=_stub_cache_row(score_source="course", effective_n=50.0, total_grade_count=100),
        key_evidence=_key_evidence(row_count=2, af_sum=50, total_sum=100),
    )
    exception_no_rows = inv.classify_section(
        crn="30002",
        subject="ABC",
        course_number="2000",
        cache_row=_stub_cache_row(score_source="subject", effective_n=50.0, total_grade_count=None),
        key_evidence=_key_evidence(),
    )
    exception_non_letter = inv.classify_section(
        crn="30003",
        subject="ABC",
        course_number="4901",
        cache_row=_stub_cache_row(score_source="course", effective_n=0, total_grade_count=20),
        key_evidence=_key_evidence(row_count=1, af_sum=0, total_sum=20),
    )
    inventory = _make_inventory((evidence_backed, exception_no_rows, exception_non_letter))
    output = inventory.to_dict()

    assert output["verdicts"] == {"integrity": "PASS", "d21_grade_coverage": "PASS"}
    assert (
        output["evidence_backed_sections"] + sum(output["exception_sections_by_reason"].values())
        == output["snapshot"]["section_count"]
    )


def test_d21_grade_coverage_fails_when_any_failure_state_present() -> None:
    evidence_backed = inv.classify_section(
        crn="30001",
        subject="ABC",
        course_number="1000",
        cache_row=_stub_cache_row(score_source="course", effective_n=50.0, total_grade_count=100),
        key_evidence=_key_evidence(row_count=2, af_sum=50, total_sum=100),
    )
    unclassified = inv.classify_section(
        crn="30004",
        subject="ABC",
        course_number="9999",
        cache_row=_stub_cache_row(score_source="bogus", effective_n=0.0, total_grade_count=None),
        key_evidence=_key_evidence(),
    )
    inventory = _make_inventory((evidence_backed, unclassified))
    output = inventory.to_dict()

    assert output["verdicts"] == {"integrity": "FAIL", "d21_grade_coverage": "FAIL"}


def test_term_batch_statement_count_does_not_grow_with_represented_courses(
    db_session: Session,
) -> None:
    next_id = iter(range(200, 300))

    def seed(course_count: int) -> None:
        for _ in range(course_count):
            course_id = next(next_id)
            _add_course(db_session, course_id=course_id, subject="ZZZ", number=f"3{course_id:03d}")
            _add_section(db_session, course_id=course_id, crn=f"9{course_id:04d}")
        db_session.commit()

    def count_statements() -> int:
        statements: list[str] = []

        def record(conn: object, cursor: object, statement: str, *_args: object) -> None:
            statements.append(statement.lower())

        engine = db_session.get_bind()
        event.listen(engine, "before_cursor_execute", record)
        try:
            inv.collect_inventory(db_session, TERM)
        finally:
            event.remove(engine, "before_cursor_execute", record)
        return len(statements)

    seed(2)
    small_total = count_statements()

    seed(6)
    large_total = count_statements()

    assert small_total == large_total


def test_help_lists_term_and_exceptions_md_flags() -> None:
    help_text = inv.build_parser().format_help()
    assert "--term" in help_text
    assert "--exceptions-md" in help_text


def test_exceptions_md_sorted_table_matches_json_exception_count(tmp_path: Path) -> None:
    exception_a = inv.classify_section(
        crn="40002",
        subject="ABC",
        course_number="1000",
        cache_row=_stub_cache_row(score_source="subject", effective_n=50.0, total_grade_count=None),
        key_evidence=_key_evidence(),
    )
    exception_b = inv.classify_section(
        crn="40001",
        subject="ABC",
        course_number="1000",
        cache_row=_stub_cache_row(score_source="subject", effective_n=50.0, total_grade_count=None),
        key_evidence=_key_evidence(),
    )
    exception_c = inv.classify_section(
        crn="40003",
        subject="AAA",
        course_number="2000",
        cache_row=_stub_cache_row(score_source="global", effective_n=0.0, total_grade_count=None),
        key_evidence=_key_evidence(),
    )
    inventory = _make_inventory((exception_a, exception_b, exception_c))
    markdown = inv.render_exceptions_markdown(inventory)

    assert "40001, 40002" in markdown  # sorted CRNs within the ABC/1000 group
    aaa_index = markdown.index("AAA")
    abc_index = markdown.index("ABC | 1000")
    assert aaa_index < abc_index  # AAA sorts before ABC

    target = tmp_path / "exceptions.md"
    inv.write_atomic(target, markdown)
    assert target.read_text(encoding="utf-8") == markdown

    section_counts = [
        int(line.split("|")[3].strip())
        for line in markdown.splitlines()
        if line.startswith("| A")
    ]
    assert sum(section_counts) == 3
