from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import scripts.validate_tampa_ingest as v
from easy_a.models import Course, GradeDistribution, Section
from easy_a.rankings.cache import SectionRankingCache
from easy_a.refresh.targets import CourseTarget, load_targets
from tests.api.test_rankings_search_sql import _historical_analytics, _provenance

NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)
TERM = "202701"
PAIR = ("CHM", "2045", "2045L")


def _add_course(session: Session, subject: str, number: str, course_id: int) -> Course:
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


def _add_section(
    session: Session, *, course_id: int, crn: str, campus: str = "Tampa", term_id: int = 1
) -> Section:
    section = Section(
        term_id=term_id,
        crn=crn,
        course_id=course_id,
        section_number="001",
        campus=campus,
        session="Full Semester",
        section_type="Lecture",
        primary_status="A",
        first_seen_at=NOW,
        last_seen_at=NOW,
    )
    session.add(section)
    session.flush()
    return section


def _add_ranking(
    session: Session,
    *,
    section: Section,
    course: Course,
    score_source: str,
    effective_n: float,
) -> SectionRankingCache:
    row = SectionRankingCache(
        section_id=section.id,
        term=TERM,
        term_name="Spring 2027",
        subject=course.subject,
        course_number=course.number,
        crn=section.crn,
        course_title=course.title,
        instructor=None,
        easiness_score=0.5,
        smoothed_withdrawal_rate=0.05,
        confidence_label="low",
        score_source=score_source,
        effective_n=effective_n,
        delivery_method=None,
        historical_analytics=_historical_analytics(easiness=0.5, withdrawal=0.05, confidence="low"),
        gened_attributes=[],
        signals=[],
        instructor_provenance=_provenance("unavailable", "section_instructors"),
        gened_provenance=_provenance("unavailable", "course_attributes"),
        signal_provenance=_provenance("unavailable", "schedule/syllabi"),
        section_provenance=_provenance("current", "sections"),
        modality={
            "delivery_method": None,
            "delivery_label": None,
            "provenance": _provenance("current", "sections.delivery_method"),
        },
    )
    session.add(row)
    session.flush()
    return row


def _seed_honest_dataset(session: Session) -> tuple[Course, Course]:
    """A base course (CHM 2045, 2 Tampa sections) and a suffix course (CHM 2045L, 1
    section) with honest rankings: one course-backed row and one honest global fallback."""
    base = _add_course(session, "CHM", "2045", course_id=1001)
    suffix = _add_course(session, "CHM", "2045L", course_id=1002)
    s1 = _add_section(session, course_id=base.id, crn="30001")
    s2 = _add_section(session, course_id=base.id, crn="30002")
    s3 = _add_section(session, course_id=suffix.id, crn="30003")
    _add_ranking(session, section=s1, course=base, score_source="course", effective_n=120.0)
    _add_ranking(session, section=s2, course=base, score_source="global", effective_n=0.0)
    _add_ranking(session, section=s3, course=suffix, score_source="global", effective_n=0.0)
    session.commit()
    return base, suffix


# --- derive_suffix_pairs -----------------------------------------------------------


def test_derive_suffix_pairs_over_real_config_yields_33() -> None:
    config = load_targets(Path("config/course_targets.toml"))
    assert len(v.derive_suffix_pairs(config.targets)) == 33


def test_derive_suffix_pairs_synthetic() -> None:
    targets = (
        CourseTarget(subject="CHM", number="2045"),
        CourseTarget(subject="CHM", number="2045L"),
        CourseTarget(subject="MAC", number="1105"),
    )
    assert v.derive_suffix_pairs(targets) == (("CHM", "2045", "2045L"),)


# --- assert_suffix_exact_ingest ----------------------------------------------------


def test_assert_suffix_exact_ingest_passes_on_honest_dataset(db_session: Session) -> None:
    _seed_honest_dataset(db_session)
    v.assert_suffix_exact_ingest(db_session, TERM, [PAIR])


def test_assert_suffix_exact_ingest_raises_on_leaked_suffix_section(db_session: Session) -> None:
    base, _suffix = _seed_honest_dataset(db_session)
    # Simulate a 2045L section mis-attributed to 2045: reassign the suffix course's
    # only stored section to the base course id.
    leaked = db_session.scalar(select(Section).where(Section.crn == "30003"))
    assert leaked is not None
    leaked.course_id = base.id
    db_session.commit()
    with pytest.raises(AssertionError, match="2045L"):
        v.assert_suffix_exact_ingest(db_session, TERM, [PAIR])


def test_assert_suffix_exact_ingest_fails_closed_when_suffix_offered_only_in_another_term(
    db_session: Session,
) -> None:
    """CHM 2045L exists in the catalog and has a section, but only in 202605
    (term_id=3), not in the 202701 (term_id=1) being validated. Stored data cannot
    tell a leak from "not offered this term", so this must fail closed (WR-02)."""
    base = _add_course(db_session, "CHM", "2045", course_id=1001)
    suffix = _add_course(db_session, "CHM", "2045L", course_id=1002)
    _add_section(db_session, course_id=base.id, crn="30001", term_id=1)
    _add_section(db_session, course_id=suffix.id, crn="30003", term_id=3)
    db_session.commit()

    with pytest.raises(AssertionError) as excinfo:
        v.assert_suffix_exact_ingest(db_session, TERM, [PAIR])
    message = str(excinfo.value)
    assert "2045L" in message
    assert TERM in message
    assert "leaked into" in message
    assert "not offered in term" in message


def test_assert_suffix_exact_ingest_passes_for_the_term_the_suffix_is_offered_in(
    db_session: Session,
) -> None:
    """The same catalog/section layout as the fails-closed test above, but validated
    against 202605 (term_id=3) -- the term CHM 2045L actually has a section in --
    must not raise, because the section-count check stays term-scoped."""
    base = _add_course(db_session, "CHM", "2045", course_id=1001)
    suffix = _add_course(db_session, "CHM", "2045L", course_id=1002)
    _add_section(db_session, course_id=base.id, crn="30001", term_id=1)
    _add_section(db_session, course_id=suffix.id, crn="30003", term_id=3)
    db_session.commit()

    v.assert_suffix_exact_ingest(db_session, "202605", [PAIR])


# --- assert_coverage_reconciled -----------------------------------------------------


def test_assert_coverage_reconciled_passes_on_honest_dataset(db_session: Session) -> None:
    _seed_honest_dataset(db_session)
    targets = (
        CourseTarget(subject="CHM", number="2045"),
        CourseTarget(subject="CHM", number="2045L"),
    )
    v.assert_coverage_reconciled(db_session, TERM, targets)


def test_assert_coverage_reconciled_auto_adds_untargeted_undergraduate_tampa_course(
    db_session: Session,
) -> None:
    """2045L is stored but not a configured target. It is an undergraduate Tampa course, so
    since Phase 09 (D-05) it is an allowed auto-add rather than a failure; before Phase 09
    this exact layout raised."""
    _seed_honest_dataset(db_session)
    targets = (CourseTarget(subject="CHM", number="2045"),)
    assert v.assert_coverage_reconciled(db_session, TERM, targets) == [("CHM", "2045L")]


# --- assert_honest_coverage ---------------------------------------------------------


def test_assert_honest_coverage_passes_on_honest_dataset(db_session: Session) -> None:
    _seed_honest_dataset(db_session)
    assert v.assert_honest_coverage(db_session, TERM) == 0


def test_assert_honest_coverage_raises_on_fabricated_course_backed_row(db_session: Session) -> None:
    _seed_honest_dataset(db_session)
    row = db_session.scalar(select(SectionRankingCache).where(SectionRankingCache.crn == "30002"))
    assert row is not None
    # Fabricate: claim course-backed history while effective_n stays 0 (D-20 violation).
    row.score_source = "course"
    db_session.commit()
    with pytest.raises(AssertionError, match="30002"):
        v.assert_honest_coverage(db_session, TERM)


# --- assert_honest_coverage: D-21 non-letter-grade exception -----------------------


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


def test_assert_honest_coverage_accepts_verified_non_letter_grade_exception(
    db_session: Session,
) -> None:
    course = _add_course(db_session, "AAA", "4900", course_id=2001)
    section = _add_section(db_session, course_id=course.id, crn="40001")
    _add_ranking(db_session, section=section, course=course, score_source="course", effective_n=0.0)
    _add_grade(db_session, term_id=2, crn="70001", course_id=course.id, s=5, u=1)
    db_session.commit()

    assert v.assert_honest_coverage(db_session, TERM) == 1


def test_assert_honest_coverage_raises_when_course_key_has_letter_grades(
    db_session: Session,
) -> None:
    course = _add_course(db_session, "AAA", "4901", course_id=2002)
    section = _add_section(db_session, course_id=course.id, crn="40002")
    _add_ranking(db_session, section=section, course=course, score_source="course", effective_n=0.0)
    _add_grade(db_session, term_id=2, crn="70002", course_id=course.id, a=5, s=1)
    db_session.commit()

    with pytest.raises(AssertionError, match="40002"):
        v.assert_honest_coverage(db_session, TERM)


def test_assert_honest_coverage_raises_on_subject_zero(db_session: Session) -> None:
    course = _add_course(db_session, "AAA", "4902", course_id=2003)
    section = _add_section(db_session, course_id=course.id, crn="40003")
    _add_ranking(
        db_session, section=section, course=course, score_source="subject", effective_n=0.0
    )
    db_session.commit()

    with pytest.raises(AssertionError, match="40003"):
        v.assert_honest_coverage(db_session, TERM)


def test_assert_honest_coverage_raises_on_instructor_course_zero_even_with_non_letter_history(
    db_session: Session,
) -> None:
    course = _add_course(db_session, "AAA", "4903", course_id=2004)
    section = _add_section(db_session, course_id=course.id, crn="40004")
    _add_ranking(
        db_session,
        section=section,
        course=course,
        score_source="instructor_course",
        effective_n=0.0,
    )
    _add_grade(db_session, term_id=2, crn="70004", course_id=course.id, s=5, u=1)
    db_session.commit()

    with pytest.raises(AssertionError, match="40004"):
        v.assert_honest_coverage(db_session, TERM)


# --- Phase 09: D-05 auto-added courses and removed sections ---------------------------

BASE_TARGETS = (
    CourseTarget(subject="CHM", number="2045"),
    CourseTarget(subject="CHM", number="2045L"),
)


def _write_targets(tmp_path: Path, targets: tuple[CourseTarget, ...]) -> Path:
    body = "".join(
        f'[[targets]]\nsubject = "{t.subject}"\nnumber = "{t.number}"\n' for t in targets
    )
    path = tmp_path / "targets.toml"
    path.write_text(
        'catalog_edition = "2026-2027"\n'
        'catalog_url_template = "https://example.edu/{subject}/{number}"\n' + body
    )
    return path


def _add_auto_added_course(
    session: Session, *, number: str = "3363", campus: str = "Tampa", crn: str = "50001"
) -> tuple[Course, Section]:
    course = _add_course(session, "AAA", number, course_id=3001)
    section = _add_section(session, course_id=course.id, crn=crn, campus=campus)
    _add_ranking(session, section=section, course=course, score_source="global", effective_n=0.0)
    session.commit()
    return course, section


def test_auto_added_undergraduate_tampa_course_passes_and_main_prints_info_line(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    _seed_honest_dataset(db_session)
    _add_auto_added_course(db_session)

    assert v.assert_coverage_reconciled(db_session, TERM, BASE_TARGETS) == [("AAA", "3363")]

    monkeypatch.setattr(v, "get_session_factory", lambda: lambda: nullcontext(db_session))
    assert v.main(["--targets", str(_write_targets(tmp_path, BASE_TARGETS))]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert "INFO auto-added (D-05): 1 course(s): AAA 3363" in lines
    assert lines.index("INFO auto-added (D-05): 1 course(s): AAA 3363") + 1 == lines.index(
        "PASS reconciliation"
    )


def test_main_prints_zero_auto_added_when_every_course_is_targeted(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    _seed_honest_dataset(db_session)
    monkeypatch.setattr(v, "get_session_factory", lambda: lambda: nullcontext(db_session))
    assert v.main(["--targets", str(_write_targets(tmp_path, BASE_TARGETS))]) == 0
    assert "INFO auto-added (D-05): 0 course(s)" in capsys.readouterr().out.splitlines()


def test_untargeted_graduate_course_fails_reconciliation(db_session: Session) -> None:
    _seed_honest_dataset(db_session)
    _add_auto_added_course(db_session, number="6000")
    with pytest.raises(AssertionError, match="6000"):
        v.assert_coverage_reconciled(db_session, TERM, BASE_TARGETS)


def test_untargeted_non_tampa_course_fails_reconciliation(db_session: Session) -> None:
    _seed_honest_dataset(db_session)
    _add_auto_added_course(db_session, number="3363", campus="St. Petersburg")
    with pytest.raises(AssertionError, match="3363"):
        v.assert_coverage_reconciled(db_session, TERM, BASE_TARGETS)


def test_reconciliation_mismatch_names_all_four_numbers(db_session: Session) -> None:
    _seed_honest_dataset(db_session)
    course, _section = _add_auto_added_course(db_session)
    # Drop the auto-added course's cache row: served total no longer matches stored.
    db_session.execute(
        SectionRankingCache.__table__.delete().where(SectionRankingCache.crn == "50001")
    )
    db_session.commit()
    with pytest.raises(AssertionError) as excinfo:
        v.assert_coverage_reconciled(db_session, TERM, BASE_TARGETS)
    message = str(excinfo.value)
    assert "stored active Section rows=4" in message
    assert "coverage_metadata sum=3" in message
    assert "auto-added active sections=1" in message
    assert "rankings-search total=3" in message
    assert course.subject == "AAA"


def test_removed_sections_are_excluded_from_every_count(db_session: Session) -> None:
    base, _suffix = _seed_honest_dataset(db_session)
    # A removed section on a targeted course, and a removed section of an untargeted
    # graduate course: neither has a cache row (the cache is built from active sections).
    removed_base = _add_section(db_session, course_id=base.id, crn="30009")
    grad = _add_course(db_session, "AAA", "6000", course_id=3002)
    removed_grad = _add_section(db_session, course_id=grad.id, crn="50009")
    removed_base.removed_at = NOW
    removed_grad.removed_at = NOW
    db_session.commit()

    assert v.assert_coverage_reconciled(db_session, TERM, BASE_TARGETS) == []
    assert v.assert_honest_coverage(db_session, TERM) == 0


def test_removed_section_with_stale_dishonest_cache_row_is_not_scanned_by_honest_coverage(
    db_session: Session,
) -> None:
    course = _add_course(db_session, "AAA", "3363", course_id=3003)
    removed = _add_section(db_session, course_id=course.id, crn="50002")
    _add_ranking(db_session, section=removed, course=course, score_source="course", effective_n=0.0)
    removed.removed_at = NOW
    db_session.commit()
    assert v.assert_honest_coverage(db_session, TERM) == 0


def test_suffix_exact_still_counts_removed_sections(db_session: Session) -> None:
    """A removed section was still ingested under the right course, so a suffix course whose
    only section is soft-removed does not trip the leak guard (raise condition unchanged)."""
    base, suffix = _seed_honest_dataset(db_session)
    only_suffix = db_session.scalar(select(Section).where(Section.crn == "30003"))
    assert only_suffix is not None
    only_suffix.removed_at = NOW
    db_session.commit()
    assert base.id and suffix.id
    v.assert_suffix_exact_ingest(db_session, TERM, [PAIR])
