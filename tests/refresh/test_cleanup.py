from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

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
from easy_a.refresh.cleanup import (
    CleanupError,
    clean_other_campus_sections,
    find_other_campus_sections,
    stored_counts,
)
from easy_a.refresh.cleanup_cli import main

NOW = datetime(2026, 9, 9, tzinfo=UTC)


def test_dry_run_reports_matches_without_deleting(db_session: Session) -> None:
    _seed(db_session, tampa=3, other=2)

    report = clean_other_campus_sections(db_session, term="202701", as_of=NOW)

    assert report.applied is False
    assert report.after is None
    assert len(report.matched) == 2
    assert {ref.campus for ref in report.matched} == {"St. Petersburg", "Sarasota-Manatee"}
    assert report.before.sections == 5
    assert report.before.kept_campus_sections == 3
    assert report.before.other_campus_sections == 2
    assert report.sections_removed == 0
    assert db_session.scalar(select(Section).where(Section.crn == "90001")) is not None


def test_apply_removes_only_other_campus_sections(db_session: Session) -> None:
    _seed(db_session, tampa=3, other=2)
    grades_before = db_session.scalars(select(GradeDistribution)).all()

    report = clean_other_campus_sections(db_session, term="202701", apply=True, as_of=NOW)

    assert report.applied is True
    assert report.sections_removed == 2
    assert report.kept_campus_sections_removed == 0
    assert report.grade_rows_removed == 0
    assert report.after is not None
    assert report.after.sections == 3
    assert report.after.other_campus_sections == 0
    assert [row.campus for row in report.after.by_campus] == ["Tampa"]
    remaining = db_session.scalars(select(Section)).all()
    assert {section.campus for section in remaining} == {"Tampa"}
    assert len(db_session.scalars(select(GradeDistribution)).all()) == len(grades_before)


def test_apply_cascades_observations_of_removed_sections_only(db_session: Session) -> None:
    _seed(db_session, tampa=2, other=2)
    before = stored_counts(db_session, "202701")

    report = clean_other_campus_sections(db_session, term="202701", apply=True, as_of=NOW)

    assert report.seat_snapshots_removed == 2
    assert report.instructor_observations_removed == 2
    assert report.after is not None
    assert report.after.seat_snapshots == before.seat_snapshots - 2
    assert report.after.instructor_observations == before.instructor_observations - 2
    surviving_ids = set(db_session.scalars(select(Section.id)).all())
    for snapshot in db_session.scalars(select(SeatSnapshot)):
        assert snapshot.section_id in surviving_ids
    for observation in db_session.scalars(select(SectionInstructor)):
        assert observation.section_id in surviving_ids


def test_grade_rows_in_other_terms_are_untouched(db_session: Session) -> None:
    _seed(db_session, tampa=1, other=1)
    _add_grade(db_session, term_id=2, crn="89033")
    before = stored_counts(db_session, "202701")
    assert before.grade_rows_all_terms > before.grade_rows_term

    report = clean_other_campus_sections(db_session, term="202701", apply=True, as_of=NOW)

    assert report.after is not None
    assert report.after.grade_rows_all_terms == before.grade_rows_all_terms
    assert report.after.grade_rows_term == before.grade_rows_term


def test_expected_count_mismatch_refuses_and_deletes_nothing(db_session: Session) -> None:
    _seed(db_session, tampa=2, other=2)

    with pytest.raises(CleanupError, match="Expected to remove 47 sections but matched 2"):
        clean_other_campus_sections(
            db_session, term="202701", apply=True, expect_removed=47, as_of=NOW
        )

    assert stored_counts(db_session, "202701").sections == 4


def test_expected_count_match_proceeds(db_session: Session) -> None:
    _seed(db_session, tampa=2, other=2)

    report = clean_other_campus_sections(
        db_session, term="202701", apply=True, expect_removed=2, as_of=NOW
    )

    assert report.sections_removed == 2


def test_sections_with_stored_syllabi_are_refused(db_session: Session) -> None:
    _seed(db_session, tampa=1, other=1)
    other = db_session.scalar(select(Section).where(Section.campus != "Tampa"))
    assert other is not None
    _add_syllabus(db_session, section=other)

    with pytest.raises(CleanupError, match="stored syllabi"):
        clean_other_campus_sections(db_session, term="202701", apply=True, as_of=NOW)

    assert stored_counts(db_session, "202701").sections == 2


def test_campus_label_comparison_ignores_case_and_padding(db_session: Session) -> None:
    _seed(db_session, tampa=1, other=0)
    _add_section(db_session, crn="90500", campus="  tampa ")

    assert find_other_campus_sections(db_session, "202701") == ()


def test_other_terms_are_out_of_scope(db_session: Session) -> None:
    _seed(db_session, tampa=1, other=1)
    _add_section(db_session, crn="80001", campus="St. Petersburg", term_id=2)

    report = clean_other_campus_sections(db_session, term="202701", apply=True, as_of=NOW)

    assert report.sections_removed == 1
    survivor = db_session.scalar(select(Section).where(Section.crn == "80001"))
    assert survivor is not None


def test_second_run_is_a_no_op(db_session: Session) -> None:
    _seed(db_session, tampa=2, other=2)
    clean_other_campus_sections(db_session, term="202701", apply=True, as_of=NOW)

    report = clean_other_campus_sections(db_session, term="202701", apply=True, as_of=NOW)

    assert report.matched == ()
    assert report.sections_removed == 0


def test_unknown_term_is_refused(db_session: Session) -> None:
    with pytest.raises(CleanupError, match="not present in the database"):
        clean_other_campus_sections(db_session, term="209901", as_of=NOW)


def test_blank_kept_campus_is_refused(db_session: Session) -> None:
    _seed(db_session, tampa=1, other=1)

    with pytest.raises(CleanupError, match="campus to keep is required"):
        clean_other_campus_sections(db_session, term="202701", kept_campus="   ", as_of=NOW)


def test_cli_dry_run_reports_without_writing(capsys: pytest.CaptureFixture[str]) -> None:
    factory = _factory(tampa=3, other=2)

    exit_code = main(["--term", "202701"], session_factory=factory)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "dry run - nothing written" in output
    assert "Matched for removal: 2" in output
    assert "Nothing was deleted" in output
    with factory() as session:
        assert stored_counts(session, "202701").sections == 5


def test_cli_apply_writes_and_reports_json(capsys: pytest.CaptureFixture[str]) -> None:
    factory = _factory(tampa=3, other=2)

    exit_code = main(["--term", "202701", "--apply", "--json"], session_factory=factory)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["applied"] is True
    assert payload["sections_removed"] == 2
    assert payload["kept_campus_sections_removed"] == 0
    assert payload["grade_rows_removed"] == 0
    assert payload["after"]["kept_campus_sections"] == 3
    with factory() as session:
        assert stored_counts(session, "202701").other_campus_sections == 0


def test_cli_expected_count_mismatch_exits_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    factory = _factory(tampa=3, other=2)

    exit_code = main(
        ["--term", "202701", "--apply", "--expect-removed", "47"], session_factory=factory
    )

    assert exit_code == 1
    assert "ERROR: Expected to remove 47 sections but matched 2" in capsys.readouterr().out
    with factory() as session:
        assert stored_counts(session, "202701").sections == 5


def _factory(*, tampa: int, other: int) -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
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
            ]
        )
        session.flush()
        _seed(session, tampa=tampa, other=other)
    return factory


_OTHER_CAMPUSES = ("St. Petersburg", "Sarasota-Manatee")


def _seed(session: Session, *, tampa: int, other: int) -> None:
    for index in range(tampa):
        _add_section(session, crn=f"9000{index}", campus="Tampa")
    for index in range(other):
        _add_section(
            session,
            crn=f"9100{index}",
            campus=_OTHER_CAMPUSES[index % len(_OTHER_CAMPUSES)],
        )
    _add_grade(session, term_id=1, crn="90000")


def _add_section(
    session: Session, *, crn: str, campus: str, term_id: int = 1, course_id: int = 10
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
    session.add(
        SectionInstructor(
            section_id=section.id,
            name_raw="Staff",
            name_normalized=None,
            source="usf_staff_schedule",
            observed_at=NOW,
        )
    )
    session.add(
        SeatSnapshot(
            section_id=section.id,
            observed_at=NOW,
            capacity=30,
            enrollment=10,
            seats_remaining=20,
            wait_seats_available=0,
        )
    )
    session.flush()
    return section


def _add_grade(session: Session, *, term_id: int, crn: str) -> None:
    session.add(
        GradeDistribution(
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
            source=f"synthetic-{term_id}-{crn}",
            source_hash="synthetic",
        )
    )
    session.flush()


def _add_syllabus(session: Session, *, section: Section) -> None:
    session.add(
        Syllabus(
            document_id=f"doc-{section.crn}",
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
    )
    session.flush()


def test_cli_apply_with_nothing_to_remove_says_so(capsys: pytest.CaptureFixture[str]) -> None:
    factory = _factory(tampa=3, other=0)

    exit_code = main(["--term", "202701", "--apply"], session_factory=factory)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Nothing to remove: no non-Tampa sections are stored for term 202701." in output
    assert "Re-run with --apply" not in output
