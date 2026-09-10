from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

import easy_a.refresh.cleanup as cleanup_module
from easy_a.db import Base
from easy_a.models import (
    Course,
    GradeDistribution,
    SeatSnapshot,
    Section,
    SectionInstructor,
    Syllabus,
    Term,
)
from easy_a.refresh.cleanup import CleanupError, clean_other_campus_sections
from easy_a.refresh.cleanup_cli import main
from easy_a.refresh.targets import CourseTarget

NOW = datetime(2026, 9, 10, tzinfo=UTC)
TARGETS = (
    CourseTarget(subject="MAC", number="1105"),
    CourseTarget(subject="ENC", number="1101"),
)


def test_dry_run_reports_exact_scope_without_deleting() -> None:
    factory = _factory()
    with factory.begin() as session:
        tampa = _add_section(session, crn="10001", campus="Tampa")
        candidate = _add_section(session, crn="10002", campus="St. Petersburg")
        before_ids = set(session.scalars(select(Section.id)))
        report = clean_other_campus_sections(session, term="202701", targets=TARGETS)

        assert report.applied is False
        assert report.after is None
        assert report.apply_safe is True
        assert [ref.section_id for ref in report.matched] == [candidate.id]
        assert report.ambiguous == ()
        assert report.before.tampa_target_sections == 1
        assert report.before.other_campus_target_sections == 1
        assert report.candidate_seat_snapshots == 1
        assert report.candidate_instructor_observations == 1
        assert report.candidate_syllabi == 0
        assert report.candidate_grade_rows == 0
        assert set(session.scalars(select(Section.id))) == before_ids == {tampa.id, candidate.id}


def test_apply_deletes_only_non_tampa_configured_target_in_term() -> None:
    factory = _factory()
    with factory.begin() as session:
        candidate = _add_section(session, crn="10002", campus="Sarasota-Manatee")
        tampa = _add_section(session, crn="10001", campus="Tampa")
        historical = _add_section(
            session, crn="80001", campus="St. Petersburg", term_id=2
        )
        unrelated = _add_section(
            session, crn="10003", campus="St. Petersburg", course_id=12
        )

        report = clean_other_campus_sections(
            session,
            term="202701",
            targets=TARGETS,
            apply=True,
            expect_removed=1,
            as_of=NOW,
        )

        remaining = set(session.scalars(select(Section.id)))
        assert candidate.id not in remaining
        assert {tampa.id, historical.id, unrelated.id} <= remaining
        assert report.sections_removed == 1
        assert report.tampa_sections_removed == 0
        assert report.historical_sections_removed == 0
        assert report.unrelated_term_sections_removed == 0


def test_apply_deletes_candidate_seats_instructors_and_linked_syllabi() -> None:
    factory = _factory()
    with factory.begin() as session:
        kept = _add_section(session, crn="10001", campus="Tampa")
        candidate = _add_section(session, crn="10002", campus="St. Petersburg")
        kept_syllabus = _add_syllabus(session, kept)
        candidate_syllabus = _add_syllabus(session, candidate)
        kept_seats = {row.id for row in kept.seat_snapshots}
        kept_instructors = {row.id for row in kept.instructors}

        report = clean_other_campus_sections(
            session,
            term="202701",
            targets=TARGETS,
            apply=True,
            expect_removed=1,
        )

        assert report.seat_snapshots_removed == 1
        assert report.instructor_observations_removed == 1
        assert report.syllabi_removed == 1
        assert set(session.scalars(select(SeatSnapshot.id))) == kept_seats
        assert set(session.scalars(select(SectionInstructor.id))) == kept_instructors
        assert set(session.scalars(select(Syllabus.id))) == {kept_syllabus.id}
        assert session.get(Syllabus, candidate_syllabus.id) is None


def test_grade_rows_are_unchanged() -> None:
    factory = _factory()
    with factory.begin() as session:
        _add_section(session, crn="10001", campus="Tampa")
        _add_section(session, crn="10002", campus="St. Petersburg")
        _add_grade(session, term_id=1, crn="10001")
        _add_grade(session, term_id=2, crn="80001")
        grade_ids = set(session.scalars(select(GradeDistribution.id)))

        report = clean_other_campus_sections(
            session,
            term="202701",
            targets=TARGETS,
            apply=True,
            expect_removed=1,
        )

        assert set(session.scalars(select(GradeDistribution.id))) == grade_ids
        assert report.grade_rows_removed == 0


def test_candidate_with_same_term_crn_grade_blocks_apply() -> None:
    factory = _factory()
    with factory.begin() as session:
        candidate = _add_section(session, crn="10002", campus="St. Petersburg")
        _add_grade(session, term_id=1, crn=candidate.crn)

        dry_run = clean_other_campus_sections(session, term="202701", targets=TARGETS)
        assert dry_run.apply_safe is False
        assert dry_run.candidate_grade_rows == 1
        assert dry_run.matched[0].grade_rows_same_term_crn == 1

        with pytest.raises(CleanupError, match="grade row"):
            clean_other_campus_sections(
                session,
                term="202701",
                targets=TARGETS,
                apply=True,
                expect_removed=1,
            )
        assert session.get(Section, candidate.id) is not None


def test_blank_campus_is_reported_as_ambiguous_and_preserved() -> None:
    factory = _factory()
    with factory.begin() as session:
        ambiguous = _add_section(session, crn="10003", campus="   ")
        candidate = _add_section(session, crn="10002", campus="St. Petersburg")

        report = clean_other_campus_sections(
            session,
            term="202701",
            targets=TARGETS,
            apply=True,
            expect_removed=1,
        )

        assert [ref.section_id for ref in report.ambiguous] == [ambiguous.id]
        assert session.get(Section, ambiguous.id) is not None
        assert session.get(Section, candidate.id) is None
        assert report.ambiguous_sections_removed == 0
        assert report.after is not None
        assert report.after.ambiguous_target_sections == 1


@pytest.mark.parametrize("campus", [None, "", "   "])
def test_null_and_blank_campus_values_classify_as_ambiguous(campus: str | None) -> None:
    assert cleanup_module._campus_kind(campus) == "ambiguous"


def test_tampa_comparison_ignores_case_and_padding() -> None:
    factory = _factory()
    with factory.begin() as session:
        kept = _add_section(session, crn="10001", campus="  tampa ")

        report = clean_other_campus_sections(session, term="202701", targets=TARGETS)

        assert report.matched == ()
        assert report.ambiguous == ()
        assert report.before.tampa_target_sections == 1
        assert session.get(Section, kept.id) is not None


def test_expected_count_mismatch_deletes_nothing() -> None:
    factory = _factory()
    with factory.begin() as session:
        candidate = _add_section(session, crn="10002", campus="St. Petersburg")

        with pytest.raises(CleanupError, match="Expected to remove 47 sections but matched 1"):
            clean_other_campus_sections(
                session,
                term="202701",
                targets=TARGETS,
                apply=True,
                expect_removed=47,
            )
        assert session.get(Section, candidate.id) is not None


def test_service_requires_expected_count_for_apply() -> None:
    factory = _factory()
    with factory.begin() as session:
        _add_section(session, crn="10002", campus="St. Petersburg")
        with pytest.raises(CleanupError, match="requires --expect-removed"):
            clean_other_campus_sections(
                session, term="202701", targets=TARGETS, apply=True
            )


def test_second_apply_is_idempotent() -> None:
    factory = _factory()
    with factory.begin() as session:
        _add_section(session, crn="10002", campus="St. Petersburg")
        clean_other_campus_sections(
            session,
            term="202701",
            targets=TARGETS,
            apply=True,
            expect_removed=1,
        )
        report = clean_other_campus_sections(
            session,
            term="202701",
            targets=TARGETS,
            apply=True,
            expect_removed=0,
        )

        assert report.matched == ()
        assert report.sections_removed == 0
        assert report.after is not None
        assert report.after.other_campus_target_sections == 0


def test_failed_post_delete_invariant_rolls_back_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = _factory()
    with factory.begin() as session:
        candidate = _add_section(session, crn="10002", campus="St. Petersburg")
        candidate_id = candidate.id

    def fail_verification(**_: object) -> None:
        raise CleanupError("forced invariant failure")

    monkeypatch.setattr(cleanup_module, "_verify_identities", fail_verification)
    with pytest.raises(CleanupError, match="forced invariant failure"), factory.begin() as session:
        clean_other_campus_sections(
            session,
            term="202701",
            targets=TARGETS,
            apply=True,
            expect_removed=1,
        )

    with factory() as session:
        assert session.get(Section, candidate_id) is not None
        assert session.scalar(select(SeatSnapshot).where(SeatSnapshot.section_id == candidate_id))
        assert session.scalar(
            select(SectionInstructor).where(SectionInstructor.section_id == candidate_id)
        )


def test_sqlite_executes_cleanup_and_reports_per_course_counts() -> None:
    factory = _factory()
    assert factory.kw["bind"].dialect.name == "sqlite"
    with factory.begin() as session:
        _add_section(session, crn="10001", campus="Tampa")
        _add_section(session, crn="10002", campus="St. Petersburg")
        _add_section(session, crn="10004", campus="Tampa", course_id=11)

        report = clean_other_campus_sections(
            session,
            term="202701",
            targets=TARGETS,
            apply=True,
            expect_removed=1,
        )

        assert report.after is not None
        assert [(row.subject, row.tampa_sections) for row in report.after.by_course] == [
            ("MAC", 1),
            ("ENC", 1),
        ]


def test_cli_dry_run_json_does_not_write(capsys: pytest.CaptureFixture[str]) -> None:
    factory = _factory()
    with factory.begin() as session:
        candidate = _add_section(session, crn="10002", campus="St. Petersburg")
        candidate_id = candidate.id

    exit_code = main(["--term", "202701", "--json"], session_factory=factory)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["applied"] is False
    assert len(payload["matched"]) == 1
    with factory() as session:
        assert session.get(Section, candidate_id) is not None


def test_cli_apply_requires_expected_count() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--term", "202701", "--apply"], session_factory=_factory())
    assert exc_info.value.code == 2


def test_postgres_cleanup_transaction_and_locks() -> None:
    url = os.environ.get("EASY_A_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set EASY_A_TEST_POSTGRES_URL to run PostgreSQL integration")
    engine = create_engine(url)
    assert engine.dialect.name == "postgresql"
    schema = "cleanup_" + uuid4().hex
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            Base.metadata.create_all(connection)
            with Session(bind=connection) as session:
                _seed_reference_rows(session)
                _add_section(session, crn="10001", campus="Tampa")
                _add_section(session, crn="10002", campus="St. Petersburg")
                report = clean_other_campus_sections(
                    session,
                    term="202701",
                    targets=TARGETS,
                    apply=True,
                    expect_removed=1,
                )
                assert report.sections_removed == 1
                assert report.after is not None
                assert report.after.tampa_target_sections == 1
                assert report.after.other_campus_target_sections == 0
            transaction.rollback()
    finally:
        engine.dispose()


def _factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
        _seed_reference_rows(session)
    return factory


def _seed_reference_rows(session: Session) -> None:
    session.add_all(
        [
            Term(id=1, banner_code="202701", name="Spring 2027", year=2027, season="Spring"),
            Term(id=2, banner_code="202408", name="Fall 2024", year=2024, season="Fall"),
            Course(
                id=10,
                subject="MAC",
                number="1105",
                title="College Algebra",
                catalog_edition="2026-2027",
            ),
            Course(
                id=11,
                subject="ENC",
                number="1101",
                title="Composition I",
                catalog_edition="2026-2027",
            ),
            Course(
                id=12,
                subject="ART",
                number="1001",
                title="Unrelated Art",
                catalog_edition="2026-2027",
            ),
        ]
    )
    session.flush()


def _add_section(
    session: Session,
    *,
    crn: str,
    campus: str,
    term_id: int = 1,
    course_id: int = 10,
) -> Section:
    section = Section(
        term_id=term_id,
        crn=crn,
        course_id=course_id,
        section_number="001",
        campus=campus,
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Active",
        delivery_method="CL",
        first_seen_at=NOW,
        last_seen_at=NOW,
    )
    session.add(section)
    session.flush()
    section.instructors.append(
        SectionInstructor(
            name_raw="Staff",
            name_normalized=None,
            source="usf_staff_schedule",
            observed_at=NOW,
        )
    )
    section.seat_snapshots.append(
        SeatSnapshot(
            observed_at=NOW,
            capacity=30,
            enrollment=10,
            seats_remaining=20,
            wait_seats_available=0,
        )
    )
    session.flush()
    return section


def _add_grade(session: Session, *, term_id: int, crn: str) -> GradeDistribution:
    grade = GradeDistribution(
        term_id=term_id,
        crn=crn,
        course_id=10,
        section_number_raw="001",
        campus_raw="Tampa",
        a_count=10,
        b_count=5,
        c_count=3,
        d_count=1,
        f_count=1,
        i_count=0,
        s_count=0,
        u_count=0,
        w_count=2,
        other_count=0,
        total_grades=22,
        source=f"test-{term_id}-{crn}",
        source_hash="test",
    )
    session.add(grade)
    session.flush()
    return grade


def _add_syllabus(session: Session, section: Section) -> Syllabus:
    syllabus = Syllabus(
        document_id=f"doc-{section.term_id}-{section.crn}",
        section_id=section.id,
        term_id=section.term_id,
        crn=section.crn,
        course_id=section.course_id,
        section_number=section.section_number,
        title="Syllabus",
        view_url="https://example.invalid/syllabus",
        content_html="<p>x</p>",
        content_text="x",
        content_hash="hash",
    )
    session.add(syllabus)
    session.flush()
    return syllabus
