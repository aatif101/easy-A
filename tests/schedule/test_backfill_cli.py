"""The backfill CLI as the D-04 rollout instrument: what-if, atomic apply, rollback, rebuild-only.

Seeds a small 202701 (live term) with one section taught by "X. Ou" and a 202408 grade history for
the same course, so the backfill moves exactly that section from course-level to instructor-course
scoring. Everything runs over SQLite and a fake USF client; nothing touches a live service.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Generator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.db import Base
from easy_a.models import (
    Course,
    GradeDistribution,
    SeatSnapshot,
    Section,
    SectionInstructor,
    SectionRankingCache,
    Syllabus,
    Term,
)
from easy_a.rankings.cache import refresh_section_rankings
from easy_a.rankings.diff import RankingDiff, diff_score_rows
from easy_a.schedule.backfill import (
    BACKFILL_SOURCE,
    delete_backfilled_sections,
    select_rollback_sections,
)
from easy_a.schedule.backfill_cli import main
from easy_a.schedule.client import StaffScheduleClient
from tests.schedule.test_backfill import client_for, run
from tests.sync.sweep_support import table_counts
from tests.sync.wholeterm_html import RowSpec

SEEDED_AT = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
LIVE_TERM = "202701"
OU_CRN = "89033"
OTHER_CRN = "89100"
LIVE_OU_CRN = "70001"
LIVE_OTHER_CRN = "70002"

ClientFactory = Callable[[], StaffScheduleClient]


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    with Session(eng) as session:
        session.add_all(
            [
                Term(id=1, banner_code=LIVE_TERM, name="Spring 2027", year=2027, season="Spring"),
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
        session.commit()
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def _grade(session: Session, *, crn: str, a: int, b: int, c: int, d: int, f: int) -> None:
    session.add(
        GradeDistribution(
            term_id=2,
            crn=crn,
            course_id=10,
            section_number_raw="001",
            a_count=a,
            b_count=b,
            c_count=c,
            d_count=d,
            f_count=f,
            total_grades=a + b + c + d + f,
            source="usf_infocenter",
            source_hash=f"hash-{crn}",
        )
    )


def _live_section(session: Session, *, crn: str, instructor: str) -> None:
    section = Section(
        term_id=1,
        crn=crn,
        course_id=10,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Active",
        delivery_method="CL",
        first_seen_at=SEEDED_AT,
        last_seen_at=SEEDED_AT,
    )
    session.add(section)
    session.flush()
    session.add(
        SectionInstructor(
            section_id=section.id,
            name_raw=instructor,
            name_normalized=None,
            source="usf_schedule_sync",
            observed_at=SEEDED_AT,
        )
    )


def seed_what_if(session_factory: sessionmaker[Session]) -> list[RowSpec]:
    """202408 grades for two MAC 1105 sections and a built 202701 cache; returns the USF rows."""
    with session_factory.begin() as session:
        _grade(session, crn=OU_CRN, a=20, b=10, c=5, d=3, f=2)  # 40 letter grades
        _grade(session, crn=OTHER_CRN, a=30, b=30, c=20, d=10, f=10)
        _live_section(session, crn=LIVE_OU_CRN, instructor="X. Ou")
        _live_section(session, crn=LIVE_OTHER_CRN, instructor="Staff")
        refresh_section_rankings(session, term=LIVE_TERM)
    return [
        RowSpec(crn=OU_CRN, subject="MAC", number="1105", instructor="X. Ou"),
        RowSpec(crn=OTHER_CRN, subject="MAC", number="1105", instructor="A. Other"),
    ]


def stored_scores(session_factory: sessionmaker[Session]) -> dict[str, tuple[Any, ...]]:
    with session_factory() as session:
        return {
            row.crn: (row.easiness_score, row.score_source, row.effective_n)
            for row in session.scalars(
                select(SectionRankingCache).where(SectionRankingCache.term == LIVE_TERM)
            )
        }


def historical_client(session_factory: sessionmaker[Session]) -> ClientFactory:
    factory, _ = client_for({"202408": seed_what_if(session_factory)})
    return factory


def dry_run(
    session_factory: sessionmaker[Session],
    client_factory: ClientFactory,
    capsys: pytest.CaptureFixture[str],
    *extra: str,
) -> tuple[int, dict[str, Any]]:
    return run(["--terms", "202408", "--dry-run", *extra], session_factory, client_factory, capsys)


def run_main_raw(
    argv: list[str],
    session_factory: sessionmaker[Session],
    client_factory: ClientFactory,
) -> int:
    return main(
        argv,
        session_factory=session_factory,
        client_factory=client_factory,
        now_fn=lambda: SEEDED_AT,
        sleep=lambda seconds: None,
    )


# --- Task 1: the dry-run what-if -----------------------------------------------------------------


def test_tracer_dry_run_reports_the_full_what_if_and_commits_nothing(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_factory = historical_client(session_factory)
    counts_before = table_counts(session_factory)
    scores_before = stored_scores(session_factory)
    assert scores_before[LIVE_OU_CRN][1] == "course"

    code, report = dry_run(session_factory, client_factory, capsys)

    assert code == 0
    assert report["mode"] == "dry_run"
    assert report["status"] == "succeeded"
    what_if = report["what_if"]
    assert what_if["term"] == LIVE_TERM

    assert what_if["code_only_parity"]["identical"] is True
    ranking = what_if["ranking_diff"]
    assert ranking["changed"] == 1
    assert ranking["transitions"] == {"course->instructor_course": 1}
    assert ranking["course_level_violations"] == []
    assert ranking["course_level_invariant"] is True
    assert "changes" not in ranking

    pairs = what_if["pairs"]
    assert pairs["pairs_total"] == 2
    assert pairs["before_term"] == LIVE_TERM
    assert what_if["verdicts"] == {
        "code_only_parity": "PASS",
        "course_level_invariant": "PASS",
        "pairs_match_reference": "FAIL",  # a one-term seed cannot match the five-term reference
    }

    assert table_counts(session_factory) == counts_before
    assert stored_scores(session_factory) == scores_before


def test_report_json_carries_the_per_section_changes_list(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    client_factory = historical_client(session_factory)
    target = tmp_path / "what-if.json"

    code, report = dry_run(session_factory, client_factory, capsys, "--report-json", str(target))

    assert code == 0
    full = json.loads(target.read_text())
    changes = full["what_if"]["ranking_diff"]["changes"]
    assert [change["crn"] for change in changes] == [LIVE_OU_CRN]
    assert changes[0]["score_source_before"] == "course"
    assert changes[0]["score_source_after"] == "instructor_course"
    assert "changes" not in report["what_if"]["ranking_diff"]
    # Everything else on stdout is also in the file.
    full["what_if"]["ranking_diff"].pop("changes")
    full["what_if"]["code_only_parity"].pop("changes", None)
    assert full == report


def test_a_tampered_stored_cache_row_fails_code_only_parity(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_factory = historical_client(session_factory)
    with session_factory.begin() as session:
        row = session.scalars(
            select(SectionRankingCache).where(SectionRankingCache.crn == LIVE_OTHER_CRN)
        ).one()
        row.easiness_score = row.easiness_score + 1.5

    code, report = dry_run(session_factory, client_factory, capsys)

    assert code == 1
    assert report["status"] == "failed"
    assert report["error_kind"] == "what_if"
    what_if = report["what_if"]
    assert what_if["verdicts"]["code_only_parity"] == "FAIL"
    assert what_if["code_only_parity"]["identical"] is False
    assert what_if["code_only_parity"]["changed"] == 1


def test_what_if_term_must_be_a_live_six_digit_term(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_factory = historical_client(session_factory)
    for bad in ("202408", "2027", "abcdef"):
        code = run_main_raw(
            ["--terms", "202408", "--dry-run", "--what-if-term", bad],
            session_factory,
            client_factory,
        )
        assert code == 2
        assert capsys.readouterr().out == ""


# --- Task 2: atomic apply ------------------------------------------------------------------------


def apply_args(*extra: str) -> list[str]:
    return ["--terms", "202408", "--apply", "--rebuild-term", LIVE_TERM, *extra]


def forbidden_client() -> StaffScheduleClient:
    raise AssertionError("no USF client may be built")


def assert_nothing_written(
    session_factory: sessionmaker[Session],
    counts_before: dict[str, int],
    scores_before: dict[str, tuple[Any, ...]],
) -> None:
    assert table_counts(session_factory) == counts_before
    assert stored_scores(session_factory) == scores_before


def test_apply_without_rebuild_term_is_a_usage_error_and_makes_no_request(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    seed_what_if(session_factory)
    counts_before = table_counts(session_factory)

    code = main(
        ["--terms", "202408", "--apply"],
        session_factory=session_factory,
        client_factory=forbidden_client,
    )

    assert code == 2
    assert capsys.readouterr().out == ""
    assert table_counts(session_factory) == counts_before


@pytest.mark.parametrize("bad", ["202408", "202701x", "2027", "", "abcdef"])
def test_rebuild_term_must_be_a_live_six_digit_term(
    bad: str,
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    seed_what_if(session_factory)
    counts_before = table_counts(session_factory)

    code = main(
        ["--terms", "202408", "--apply", "--rebuild-term", bad],
        session_factory=session_factory,
        client_factory=forbidden_client,
    )

    assert code == 2
    assert capsys.readouterr().out == ""
    assert table_counts(session_factory) == counts_before


def test_expect_inserted_is_only_valid_with_apply(
    session_factory: sessionmaker[Session],
) -> None:
    code = main(
        ["--terms", "202408", "--dry-run", "--expect-inserted", "2"],
        session_factory=session_factory,
        client_factory=forbidden_client,
    )
    assert code == 2


def test_apply_commits_the_backfill_and_the_rebuilt_cache_together(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_factory = historical_client(session_factory)
    other_before = stored_scores(session_factory)[LIVE_OTHER_CRN]

    code, report = run(
        apply_args("--expect-inserted", "2"), session_factory, client_factory, capsys
    )

    assert code == 0
    assert report["mode"] == "apply"
    assert report["status"] == "succeeded"
    assert report["written"] is True
    assert "what_if" not in report
    applied = report["applied"]
    assert applied["rebuild_term"] == LIVE_TERM
    assert applied["rows_rebuilt"] == 2
    assert applied["changed"] == 1
    assert applied["transitions"] == {"course->instructor_course": 1}
    assert applied["verdicts"] == {"course_level_invariant": "PASS"}
    assert applied["gate_failures"] == []
    assert applied["expect_inserted"] == {"expected": 2, "actual": 2, "matched": True}

    counts = table_counts(session_factory)
    assert counts["Section"] == 4  # two live sections plus the two backfilled ones
    assert counts["IngestRun"] == 1
    assert counts["SeatSnapshot"] == 0
    scores = stored_scores(session_factory)
    assert scores[LIVE_OU_CRN][1] == "instructor_course"
    assert scores[LIVE_OTHER_CRN] == other_before


def test_apply_takes_the_sweep_lock_before_any_statement(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_factory = historical_client(session_factory)
    calls: list[bool] = []

    def lock(session: Session) -> bool:
        calls.append(session.in_transaction())  # no statement has run on this session yet
        return True

    monkeypatch.setattr("easy_a.schedule.backfill_cli.try_sweep_lock", lock)

    code, _ = run(apply_args(), session_factory, client_factory, capsys)

    assert code == 0
    assert calls == [False]


def test_busy_sweep_lock_exits_2_with_nothing_written(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_factory = historical_client(session_factory)
    counts_before = table_counts(session_factory)
    scores_before = stored_scores(session_factory)
    monkeypatch.setattr("easy_a.schedule.backfill_cli.try_sweep_lock", lambda session: False)

    code, report = run(apply_args(), session_factory, client_factory, capsys)

    assert code == 2
    assert report["status"] == "busy"
    assert report["error_kind"] == "sweep_lock_busy"
    assert report["written"] is False
    assert_nothing_written(session_factory, counts_before, scores_before)


def test_expect_inserted_mismatch_rolls_back_and_names_both_counts(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_factory = historical_client(session_factory)
    counts_before = table_counts(session_factory)
    scores_before = stored_scores(session_factory)

    code, report = run(
        apply_args("--expect-inserted", "999"), session_factory, client_factory, capsys
    )

    assert code == 1
    assert report["status"] == "failed"
    assert report["error_kind"] == "expect_inserted"
    assert report["written"] is False
    assert report["applied"]["expect_inserted"] == {
        "expected": 999,
        "actual": 2,
        "matched": False,
    }
    assert report["applied"]["gate_failures"] == ["expect_inserted"]
    assert_nothing_written(session_factory, counts_before, scores_before)


def test_a_course_level_violation_rolls_the_apply_back(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_factory = historical_client(session_factory)
    counts_before = table_counts(session_factory)
    scores_before = stored_scores(session_factory)
    real_diff = diff_score_rows

    def with_a_violation(before: Any, after: Any, **kwargs: Any) -> RankingDiff:
        diff = real_diff(before, after, **kwargs)
        violation = {"crn": LIVE_OTHER_CRN, "changed_fields": ["easiness_score"]}
        return replace(diff, course_level_violations=(violation,))

    monkeypatch.setattr("easy_a.schedule.backfill_cli.diff_score_rows", with_a_violation)

    code, report = run(apply_args(), session_factory, client_factory, capsys)

    assert code == 1
    assert report["error_kind"] == "course_level_invariant"
    assert report["written"] is False
    assert report["applied"]["verdicts"] == {"course_level_invariant": "FAIL"}
    assert_nothing_written(session_factory, counts_before, scores_before)


def test_a_failed_guard_in_apply_takes_no_lock_and_writes_nothing(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_what_if(session_factory)
    client_factory, _ = client_for({"202408": []})  # zero parsed rows: the zero_rows guard
    counts_before = table_counts(session_factory)
    scores_before = stored_scores(session_factory)

    code, report = run(apply_args(), session_factory, client_factory, capsys)

    assert code == 1
    assert report["error_kind"] == "guard"
    assert "applied" not in report
    assert_nothing_written(session_factory, counts_before, scores_before)


# --- Task 3: rollback and rebuild-only -----------------------------------------------------------


def undo_args(mode: str, *extra: str) -> list[str]:
    return [mode, "--rebuild-term", LIVE_TERM, *extra]


def run_undo(
    argv: list[str],
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, dict[str, Any]]:
    """Run an undo mode with a client factory that fails the test if a request is prepared."""
    return run(argv, session_factory, forbidden_client, capsys)


def apply_seed(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> tuple[dict[str, int], dict[str, tuple[Any, ...]]]:
    """Seed, apply the backfill, and return the table counts and stored scores from before it."""
    client_factory = historical_client(session_factory)
    counts_before = table_counts(session_factory)
    scores_before = stored_scores(session_factory)
    code, _ = run(apply_args(), session_factory, client_factory, capsys)
    assert code == 0
    assert stored_scores(session_factory)[LIVE_OU_CRN][1] == "instructor_course"
    return counts_before, scores_before


def section_id(session: Session, crn: str, term: str = "202408") -> int:
    return session.scalars(
        select(Section.id)
        .join(Term, Section.term_id == Term.id)
        .where(Term.banner_code == term, Section.crn == crn)
    ).one()


def test_rollback_without_yes_previews_and_writes_nothing(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    apply_seed(session_factory, capsys)
    counts_applied = table_counts(session_factory)
    scores_applied = stored_scores(session_factory)

    code, report = run_undo(undo_args("--rollback"), session_factory, capsys)

    assert code == 0
    assert report["mode"] == "rollback"
    assert report["preview"] is True
    assert report["written"] is False
    assert report["terms"]["202408"] == {"eligible_sections": 2, "ineligible_sections": 0}
    assert report["terms"]["202501"] == {"eligible_sections": 0, "ineligible_sections": 0}
    assert report["deleted_sections"] == 2  # what the commit would delete
    assert report["applied"]["transitions"] == {"instructor_course->course": 1}
    assert table_counts(session_factory) == counts_applied
    assert stored_scores(session_factory) == scores_applied


def test_rollback_yes_restores_the_pre_apply_state_except_the_ingest_run(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    counts_before, scores_before = apply_seed(session_factory, capsys)

    code, report = run_undo(undo_args("--rollback", "--yes"), session_factory, capsys)

    assert code == 0
    assert report["preview"] is False
    assert report["written"] is True
    assert report["deleted_sections"] == 2
    counts_after = table_counts(session_factory)
    assert counts_after["IngestRun"] == 1
    assert {**counts_after, "IngestRun": 0} == counts_before
    assert stored_scores(session_factory) == scores_before
    assert stored_scores(session_factory)[LIVE_OU_CRN][1] == "course"
    with session_factory() as session:
        assert session.scalars(select(Section.crn).join(Term).where(Term.id == 2)).all() == []


@pytest.mark.parametrize(
    "reason", ["seat_snapshot", "syllabus", "other_instructor", "no_instructor"]
)
def test_a_historical_section_with_other_data_is_ineligible_and_kept(
    reason: str,
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    apply_seed(session_factory, capsys)
    with session_factory.begin() as session:
        ou_id = section_id(session, OU_CRN)
        if reason == "seat_snapshot":
            session.add(SeatSnapshot(section_id=ou_id, observed_at=SEEDED_AT, capacity=30))
        elif reason == "syllabus":
            session.add(
                Syllabus(
                    document_id="doc-1",
                    section_id=ou_id,
                    term_id=2,
                    crn=OU_CRN,
                    course_id=10,
                    section_number="001",
                    title="Syllabus",
                    view_url="https://example.invalid/syllabus",
                    content_html="<p>x</p>",
                    content_text="x",
                    content_hash="0" * 64,
                )
            )
        elif reason == "other_instructor":
            session.add(
                SectionInstructor(
                    section_id=ou_id,
                    name_raw="Z. Else",
                    name_normalized=None,
                    source="usf_schedule_sync",
                    observed_at=SEEDED_AT,
                )
            )
        else:
            session.execute(delete(SectionInstructor).where(SectionInstructor.section_id == ou_id))

    code, preview = run_undo(undo_args("--rollback"), session_factory, capsys)
    assert code == 0
    assert preview["terms"]["202408"] == {"eligible_sections": 1, "ineligible_sections": 1}

    code, report = run_undo(undo_args("--rollback", "--yes"), session_factory, capsys)

    assert code == 0
    assert report["deleted_sections"] == 1
    with session_factory() as session:
        remaining = session.scalars(select(Section.crn).where(Section.term_id == 2)).all()
        assert remaining == [OU_CRN]
        # No orphaned instructor rows are left behind for the deleted section.
        live_ids = select(Section.id)
        orphans = session.scalars(
            select(SectionInstructor.id).where(SectionInstructor.section_id.not_in(live_ids))
        ).all()
        assert orphans == []


def test_live_term_sections_are_never_eligible(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    apply_seed(session_factory, capsys)
    with session_factory.begin() as session:
        live_id = section_id(session, LIVE_OU_CRN, LIVE_TERM)
        # Adversarial: a live section whose only instructor row claims the backfill as its source.
        session.execute(delete(SectionInstructor).where(SectionInstructor.section_id == live_id))
        session.add(
            SectionInstructor(
                section_id=live_id,
                name_raw="X. Ou",
                name_normalized=None,
                source=BACKFILL_SOURCE,
                observed_at=SEEDED_AT,
            )
        )

    with session_factory() as session:
        selection = select_rollback_sections(session, [LIVE_TERM, "202408"])
        assert live_id not in selection.section_ids
        assert set(selection.eligible_by_term) == {"202408"}
        assert select_rollback_sections(session, [LIVE_TERM]).section_ids == ()

    with session_factory.begin() as session:
        # Even handed its id, the delete cannot touch a live-term section.
        assert delete_backfilled_sections(session, [live_id]) == 0

    code, _ = run_undo(undo_args("--rollback", "--yes"), session_factory, capsys)
    assert code == 0
    with session_factory() as session:
        crns = session.scalars(select(Section.crn).where(Section.term_id == 1)).all()
        assert sorted(crns) == [LIVE_OU_CRN, LIVE_OTHER_CRN]


def test_rebuild_only_rebuilds_the_cache_with_no_request_and_no_data_write(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    apply_seed(session_factory, capsys)
    scores_applied = stored_scores(session_factory)
    with session_factory.begin() as session:
        row = session.scalars(
            select(SectionRankingCache).where(SectionRankingCache.crn == LIVE_OU_CRN)
        ).one()
        row.easiness_score = row.easiness_score - 7.0  # a stale cache, as after a scoring change
    counts_before = table_counts(session_factory)
    assert stored_scores(session_factory) != scores_applied

    code, report = run_undo(undo_args("--rebuild-only"), session_factory, capsys)

    assert code == 0
    assert report["mode"] == "rebuild_only"
    assert report["written"] is True
    assert "terms" not in report
    assert report["applied"]["changed"] == 1
    assert report["applied"]["gated"] is False
    assert table_counts(session_factory) == counts_before
    assert stored_scores(session_factory) == scores_applied


@pytest.mark.parametrize("flags", [["--rollback", "--yes"], ["--rebuild-only"]])
def test_busy_sweep_lock_stops_rollback_and_rebuild_only(
    flags: list[str],
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    apply_seed(session_factory, capsys)
    counts_applied = table_counts(session_factory)
    scores_applied = stored_scores(session_factory)
    monkeypatch.setattr("easy_a.schedule.backfill_cli.try_sweep_lock", lambda session: False)

    code, report = run_undo(undo_args(*flags), session_factory, capsys)

    assert code == 2
    assert report["status"] == "busy"
    assert report["written"] is False
    assert_nothing_written(session_factory, counts_applied, scores_applied)


@pytest.mark.parametrize(
    "argv",
    [
        ["--dry-run", "--apply"],
        ["--apply", "--rollback"],
        ["--rollback", "--rebuild-only"],
        ["--dry-run", "--rebuild-only"],
    ],
)
def test_modes_are_mutually_exclusive(
    argv: list[str],
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(
        [*argv, "--rebuild-term", LIVE_TERM],
        session_factory=session_factory,
        client_factory=forbidden_client,
    )
    assert code == 2
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "argv",
    [["--rollback"], ["--rebuild-only"], ["--rollback", "--yes"], ["--dry-run", "--yes"]],
)
def test_undo_modes_need_rebuild_term_and_yes_needs_rollback(
    argv: list[str],
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    if "--dry-run" in argv:
        argv = [*argv, "--rebuild-term", LIVE_TERM]
    code = main(argv, session_factory=session_factory, client_factory=forbidden_client)
    assert code == 2
    assert capsys.readouterr().out == ""


def test_help_lists_the_rollout_flags(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    text = capsys.readouterr().out
    for flag in (
        "--what-if-term",
        "--rebuild-term",
        "--expect-inserted",
        "--rollback",
        "--rebuild-only",
        "--yes",
    ):
        assert flag in text
