from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from easy_a.db import Base
from easy_a.models import (
    Course,
    GradeDistribution,
    Section,
    SectionInstructor,
    SectionRankingCache,
    Term,
)
from easy_a.rankings.cache import refresh_section_rankings
from easy_a.rankings.diff import (
    FLOAT_SCORE_FIELDS,
    SCORE_FIELDS,
    SCORE_TOLERANCE,
    ScoreRow,
    computed_score_rows,
    diff_score_rows,
    rank_rows,
    stored_score_rows,
)

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts/report_ranking_diff.py"
_spec = importlib.util.spec_from_file_location("report_ranking_diff", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
report = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = report
_spec.loader.exec_module(report)

AS_OF = datetime(2026, 9, 20, 12, tzinfo=UTC)


def _row(
    crn: str,
    *,
    easiness: float = 70.0,
    source: str = "course",
    subject: str = "MAC",
    number: str = "1105",
    withdrawal: float = 0.1,
    effective_n: float = 100.0,
    label: str = "high",
    mapped: int = 0,
) -> ScoreRow:
    return ScoreRow(
        crn=crn,
        subject=subject,
        course_number=number,
        easiness_score=easiness,
        smoothed_withdrawal_rate=withdrawal,
        effective_n=effective_n,
        confidence_label=label,
        score_source=source,
        mapped_instructor_section_count=mapped,
    )


def _rows(*rows: ScoreRow) -> dict[str, ScoreRow]:
    return {row.crn: row for row in rows}


def test_score_fields_name_the_five_compared_fields() -> None:
    assert SCORE_FIELDS == (
        "easiness_score",
        "smoothed_withdrawal_rate",
        "effective_n",
        "confidence_label",
        "score_source",
    )


def test_identical_sets_are_identical_and_invariant() -> None:
    before = _rows(_row("1"), _row("2", easiness=60.0))
    diff = diff_score_rows(before, dict(before))

    assert diff.identical
    assert diff.course_level_invariant
    assert diff.changed == 0
    assert diff.transitions == {}
    assert diff.course_level_violations == ()
    assert diff.abs_delta_buckets["0"] == 2


def test_course_to_instructor_course_move_is_a_transition_not_a_violation() -> None:
    before = _rows(_row("1", easiness=70.0), _row("2", easiness=69.0), _row("3", easiness=50.0))
    after = _rows(
        _row("1", easiness=70.6, source="instructor_course", effective_n=45.0, label="medium"),
        _row("2", easiness=69.0),
        _row("3", easiness=50.0),
    )

    diff = diff_score_rows(before, after)

    assert diff.changed == 1
    assert diff.transitions == {"course->instructor_course": 1}
    assert diff.course_level_violations == ()
    assert diff.course_level_invariant
    assert not diff.identical
    (record,) = diff.top_changes
    assert record["crn"] == "1"
    assert record["delta"] == pytest.approx(0.6)
    assert record["rank_before"] == 1
    assert record["rank_after"] == 1
    assert record["effective_n_before"] == 100.0
    assert record["effective_n_after"] == 45.0
    assert record["score_source_before"] == "course"
    assert record["score_source_after"] == "instructor_course"


def test_course_level_row_that_moves_is_a_violation() -> None:
    before = _rows(_row("1"), _row("2", source="subject"))
    after = _rows(_row("1", easiness=71.0), _row("2", source="subject"))

    diff = diff_score_rows(before, after)

    assert not diff.identical
    assert not diff.course_level_invariant
    assert [record["crn"] for record in diff.course_level_violations] == ["1"]
    assert diff.course_level_violations[0]["changed_fields"] == ["easiness_score"]


@pytest.mark.parametrize(
    "field, value",
    [
        ("withdrawal", 0.2),
        ("effective_n", 99.0),
        ("label", "low"),
    ],
)
def test_every_score_field_change_is_a_course_level_violation(field: str, value: Any) -> None:
    before = _rows(_row("1"))
    after = _rows(_row("1", **{field: value}))

    diff = diff_score_rows(before, after)

    assert diff.changed == 1
    assert [record["crn"] for record in diff.course_level_violations] == ["1"]


def test_source_change_between_course_level_sources_is_a_violation() -> None:
    diff = diff_score_rows(_rows(_row("1")), _rows(_row("1", source="subject")))

    assert diff.transitions == {"course->subject": 1}
    assert [record["crn"] for record in diff.course_level_violations] == ["1"]


def test_instructor_course_row_changing_is_not_a_course_level_violation() -> None:
    before = _rows(_row("1", source="instructor_course", easiness=80.0))
    after = _rows(_row("1", source="instructor_course", easiness=75.0))

    diff = diff_score_rows(before, after)

    assert diff.changed == 1
    assert diff.course_level_violations == ()


def test_crn_present_on_one_side_only_fails_both_verdicts() -> None:
    diff = diff_score_rows(_rows(_row("1"), _row("2")), _rows(_row("1"), _row("3")))

    assert diff.missing_in_after == ("2",)
    assert diff.extra_in_after == ("3",)
    assert not diff.identical
    assert not diff.course_level_invariant
    assert diff.total_before == 2
    assert diff.total_after == 2


def test_mapped_count_change_alone_is_informational() -> None:
    before = _rows(_row("1", mapped=0), _row("2", mapped=3))
    after = _rows(_row("1", mapped=5), _row("2", mapped=3))

    diff = diff_score_rows(before, after)

    assert diff.informational_changes == 1
    assert diff.changed == 0
    assert diff.identical
    assert diff.course_level_invariant


def test_ranks_use_easiness_desc_with_course_and_crn_tiebreak() -> None:
    rows = [
        _row("30", easiness=80.0, subject="ZZZ", number="1000"),
        _row("20", easiness=80.0, subject="AAA", number="2000"),
        _row("10", easiness=80.0, subject="AAA", number="2000"),
        _row("40", easiness=90.0, subject="MMM", number="3000"),
        _row("50", easiness=10.0, subject="AAA", number="1000"),
    ]

    assert rank_rows(rows) == {"40": 1, "10": 2, "20": 3, "30": 4, "50": 5}


def test_rank_shift_and_top_changes_ordering() -> None:
    before = _rows(
        _row("1", easiness=90.0),
        _row("2", easiness=80.0),
        _row("3", easiness=70.0),
        _row("4", easiness=60.0),
    )
    after = _rows(
        _row("1", easiness=90.0),
        _row("2", easiness=80.0),
        _row("3", easiness=70.0),
        _row("4", easiness=95.0, source="instructor_course"),
    )

    diff = diff_score_rows(before, after, top=1)

    assert diff.rank_shift["max"] == 3.0
    assert len(diff.top_changes) == 1
    assert diff.top_changes[0]["crn"] == "4"
    assert diff.top_changes[0]["rank_before"] == 4
    assert diff.top_changes[0]["rank_after"] == 1
    assert len(diff.changes) == 1


def test_abs_delta_stats_and_buckets() -> None:
    deltas = [0.0, 0.1, 0.25, 0.3, 0.9, 1.5, 2.5, 3.0, 0.0, 0.0]
    before = _rows(*[_row(str(index)) for index in range(len(deltas))])
    after = _rows(
        *[
            _row(str(index), easiness=70.0 + delta, source="instructor_course")
            for index, delta in enumerate(deltas)
        ]
    )

    diff = diff_score_rows(before, after)

    assert diff.abs_delta_buckets == {
        "0": 3,
        "(0,0.25]": 2,
        "(0.25,0.5]": 1,
        "(0.5,1]": 1,
        "(1,2]": 1,
        ">2": 2,
    }
    assert diff.abs_delta["max"] == pytest.approx(3.0)
    assert diff.abs_delta["mean"] == pytest.approx(sum(deltas) / len(deltas))
    assert diff.abs_delta["median"] == pytest.approx(0.275)
    assert diff.abs_delta["p90"] == pytest.approx(2.5)


def test_empty_inputs_are_identical() -> None:
    diff = diff_score_rows({}, {})

    assert diff.identical
    assert diff.abs_delta == {"max": 0.0, "mean": 0.0, "median": 0.0, "p90": 0.0}
    assert diff.rank_shift == {"max": 0.0, "median": 0.0}


def test_to_dict_omits_changes_unless_requested() -> None:
    diff = diff_score_rows(_rows(_row("1")), _rows(_row("1", easiness=71.0)))

    summary = diff.to_dict()
    full = diff.to_dict(include_changes=True)

    assert "changes" not in summary
    assert [record["crn"] for record in full["changes"]] == ["1"]
    assert summary["identical"] is False
    json.dumps(full)


# --- float tolerance (Phase 10 gap fix) ------------------------------------------------------

_WITHIN = SCORE_TOLERANCE / 10  # 1e-10: float noise
_BEYOND = SCORE_TOLERANCE * 2  # 2e-9: a real difference


def test_tolerance_is_a_named_one_nano_constant_on_the_two_float_fields() -> None:
    assert SCORE_TOLERANCE == 1e-9
    assert FLOAT_SCORE_FIELDS == ("easiness_score", "smoothed_withdrawal_rate")
    assert set(FLOAT_SCORE_FIELDS) <= set(SCORE_FIELDS)


@pytest.mark.parametrize("field", ["easiness", "withdrawal"])
@pytest.mark.parametrize("sign", [1, -1])
def test_float_noise_within_tolerance_is_identical_and_reported(field: str, sign: int) -> None:
    base = 70.0 if field == "easiness" else 0.1
    before = _rows(_row("1"), _row("2", easiness=60.0))
    after = _rows(_row("1", **{field: base + sign * _WITHIN}), _row("2", easiness=60.0))

    diff = diff_score_rows(before, after)

    assert diff.identical
    assert diff.course_level_invariant
    assert diff.changed == 0
    assert diff.changes == ()
    assert diff.course_level_violations == ()
    assert diff.transitions == {}
    assert diff.float_noise_count == 1
    assert diff.float_noise_max_abs_delta == pytest.approx(_WITHIN, rel=1e-3)
    noise = diff.to_dict()["float_noise"]
    assert noise["tolerance"] == SCORE_TOLERANCE
    assert noise["count"] == 1
    assert noise["max_abs_delta"] == pytest.approx(_WITHIN, rel=1e-3)


def test_float_noise_exactly_at_the_tolerance_is_still_noise() -> None:
    before = _rows(_row("1", easiness=0.0))
    after = _rows(_row("1", easiness=SCORE_TOLERANCE))

    diff = diff_score_rows(before, after)

    assert diff.identical
    assert diff.float_noise_count == 1


@pytest.mark.parametrize("field", ["easiness", "withdrawal"])
@pytest.mark.parametrize("sign", [1, -1])
def test_difference_just_beyond_tolerance_is_a_real_change(field: str, sign: int) -> None:
    base = 70.0 if field == "easiness" else 0.1
    before = _rows(_row("1"), _row("2", easiness=60.0))
    after = _rows(_row("1", **{field: base + sign * _BEYOND}), _row("2", easiness=60.0))

    diff = diff_score_rows(before, after)

    assert not diff.identical
    assert not diff.course_level_invariant
    assert diff.changed == 1
    assert [record["crn"] for record in diff.course_level_violations] == ["1"]
    assert diff.course_level_violations[0]["changed_fields"] == [
        "easiness_score" if field == "easiness" else "smoothed_withdrawal_rate"
    ]
    assert diff.float_noise_count == 0
    assert diff.float_noise_max_abs_delta == 0.0


def test_noise_on_one_float_field_does_not_hide_a_real_change_on_the_other() -> None:
    before = _rows(_row("1"))
    after = _rows(_row("1", easiness=70.0 + _WITHIN, withdrawal=0.1 + _BEYOND))

    diff = diff_score_rows(before, after)

    assert not diff.identical
    assert diff.changed == 1
    assert diff.changes[0]["changed_fields"] == ["smoothed_withdrawal_rate"]
    assert diff.float_noise_count == 1  # the easiness noise is still counted, not hidden


def test_noise_count_is_per_section_and_max_spans_both_fields() -> None:
    before = _rows(_row("1"), _row("2", easiness=60.0), _row("3", easiness=50.0))
    after = _rows(
        _row("1", easiness=70.0 + 1e-12, withdrawal=0.1 + 5e-10),
        _row("2", easiness=60.0 - 3e-11),
        _row("3", easiness=50.0),
    )

    diff = diff_score_rows(before, after)

    assert diff.identical
    assert diff.float_noise_count == 2
    assert diff.float_noise_max_abs_delta == pytest.approx(5e-10, rel=1e-3)


@pytest.mark.parametrize(
    "overrides",
    [
        {"effective_n": 100.0 + _WITHIN},  # effective_n is a count: exact, never tolerant
        {"label": "medium"},
        {"source": "subject"},
    ],
)
def test_non_float_fields_stay_exact_even_for_tiny_differences(overrides: dict[str, Any]) -> None:
    diff = diff_score_rows(_rows(_row("1")), _rows(_row("1", **overrides)))

    assert not diff.identical
    assert not diff.course_level_invariant
    assert diff.changed == 1


def test_nan_score_is_never_treated_as_noise() -> None:
    diff = diff_score_rows(_rows(_row("1")), _rows(_row("1", easiness=float("nan"))))

    assert not diff.identical
    assert diff.changed == 1


def test_a_rank_flip_from_float_noise_alone_is_not_identical() -> None:
    before = _rows(_row("1", easiness=70.0), _row("2", easiness=70.0 - _WITHIN))
    after = _rows(_row("1", easiness=70.0 - _WITHIN), _row("2", easiness=70.0))

    diff = diff_score_rows(before, after)

    assert diff.changed == 0
    assert diff.rank_shift["max"] == 1.0
    assert not diff.identical


def test_missing_and_extra_crns_still_fail_with_only_noise_elsewhere() -> None:
    diff = diff_score_rows(
        _rows(_row("1"), _row("2")), _rows(_row("1", easiness=70.0 + _WITHIN), _row("3"))
    )

    assert not diff.identical
    assert not diff.course_level_invariant


# --- database-backed tests -------------------------------------------------------------------


@pytest.fixture
def file_engine(tmp_path: Path) -> Generator[Engine, None, None]:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'diff.sqlite3'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
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
                    subject="MAC",
                    number="2311",
                    title="Calculus I",
                    catalog_edition="2026-2027",
                ),
            ]
        )
        session.commit()
    yield engine
    engine.dispose()


def _seed_grade(session: Session, *, course_id: int, crn: str, a: int, b: int, w: int) -> None:
    session.add(
        GradeDistribution(
            term_id=2,
            crn=crn,
            course_id=course_id,
            section_number_raw="001",
            section_suffix_raw=None,
            campus_raw="Tampa",
            a_count=a,
            b_count=b,
            c_count=0,
            d_count=0,
            f_count=0,
            i_count=0,
            s_count=0,
            u_count=0,
            w_count=w,
            other_count=0,
            total_grades=a + b + w,
            source=f"diff-{course_id}-{crn}",
            source_hash="diff",
        )
    )


def _seed_section(
    session: Session,
    *,
    course_id: int,
    crn: str,
    instructor: str | None,
    removed: bool = False,
) -> None:
    section = Section(
        term_id=1,
        crn=crn,
        course_id=course_id,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Active",
        delivery_method="CL",
        first_seen_at=AS_OF,
        last_seen_at=AS_OF,
        removed_at=AS_OF if removed else None,
    )
    session.add(section)
    session.flush()
    if instructor is not None:
        session.add(
            SectionInstructor(
                section_id=section.id,
                name_raw=instructor,
                name_normalized=instructor.lower(),
                source="diff-test",
                observed_at=AS_OF,
            )
        )


def _seed_term(session: Session) -> None:
    _seed_grade(session, course_id=10, crn="89033", a=80, b=20, w=5)
    _seed_grade(session, course_id=12, crn="89034", a=40, b=40, w=10)
    _seed_section(session, course_id=10, crn="70001", instructor="I. Rothstein")
    _seed_section(session, course_id=10, crn="70002", instructor="Staff")
    _seed_section(session, course_id=11, crn="70003", instructor=None)
    _seed_section(session, course_id=12, crn="70004", instructor="J. Smith")
    _seed_section(session, course_id=12, crn="70005", instructor=None, removed=True)
    session.commit()
    refresh_section_rankings(session, term="202701")
    session.commit()


def test_stored_and_computed_rows_match_after_refresh(file_engine: Engine) -> None:
    with Session(file_engine) as session:
        _seed_term(session)

        stored = stored_score_rows(session, "202701")
        computed = computed_score_rows(session, "202701")

    assert set(stored) == {"70001", "70002", "70003", "70004"}
    assert stored == computed
    diff = diff_score_rows(stored, computed)
    assert diff.identical
    assert diff.course_level_invariant
    assert diff.changed == 0


def test_computed_rows_exclude_removed_sections_and_support_term_int(file_engine: Engine) -> None:
    with Session(file_engine) as session:
        _seed_term(session)

        computed = computed_score_rows(session, 202701)

    assert "70005" not in computed


def test_editing_a_stored_course_level_row_is_reported(file_engine: Engine) -> None:
    with Session(file_engine) as session:
        _seed_term(session)
        cache_row = session.scalars(
            select(SectionRankingCache).where(SectionRankingCache.crn == "70001")
        ).one()
        assert cache_row.score_source == "course"
        cache_row.easiness_score = cache_row.easiness_score + 1.5
        session.commit()

        diff = diff_score_rows(
            stored_score_rows(session, "202701"), computed_score_rows(session, "202701")
        )

    assert not diff.identical
    assert not diff.course_level_invariant
    assert [record["crn"] for record in diff.course_level_violations] == ["70001"]
    assert diff.top_changes[0]["delta"] == pytest.approx(-1.5)


def _tamper_stored_easiness(engine: Engine, crn: str, delta: float) -> None:
    with Session(engine) as session:
        cache_row = session.scalars(
            select(SectionRankingCache).where(SectionRankingCache.crn == crn)
        ).one()
        cache_row.easiness_score = cache_row.easiness_score + delta
        session.commit()


def _run_main(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    engine: Engine,
    *argv: str,
) -> tuple[int, str]:
    monkeypatch.setattr(report, "get_engine", lambda: engine)
    code = report.main(list(argv))
    return code, capsys.readouterr().out


def test_script_exit_0_on_fresh_cache_then_1_after_mutation(
    file_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    with Session(file_engine) as session:
        _seed_term(session)

    code, out = _run_main(monkeypatch, capsys, file_engine, "--term", "202701")
    payload = json.loads(out)
    assert code == 0
    assert payload["verdicts"] == {"identical": "PASS", "course_level_invariant": "PASS"}
    assert payload["changed"] == 0
    assert payload["term"] == "202701"
    assert "://" not in out
    assert "changes" not in payload

    with Session(file_engine) as session:
        cache_row = session.scalars(
            select(SectionRankingCache).where(SectionRankingCache.crn == "70001")
        ).one()
        cache_row.easiness_score = cache_row.easiness_score + 2.0
        session.commit()

    report_path = tmp_path / "out" / "diff.json"
    code, out = _run_main(
        monkeypatch,
        capsys,
        file_engine,
        "--term",
        "202701",
        "--report-json",
        str(report_path),
    )
    payload = json.loads(out)
    assert code == 1
    assert payload["verdicts"] == {"identical": "FAIL", "course_level_invariant": "FAIL"}
    assert [record["crn"] for record in payload["course_level_violations"]] == ["70001"]
    assert "://" not in out
    assert "changes" not in payload
    full = json.loads(report_path.read_text(encoding="utf-8"))
    assert [record["crn"] for record in full["changes"]] == ["70001"]


def test_script_exit_0_when_stored_cache_differs_only_by_float_noise(
    file_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with Session(file_engine) as session:
        _seed_term(session)
    _tamper_stored_easiness(file_engine, "70001", 1e-12)

    code, out = _run_main(monkeypatch, capsys, file_engine, "--term", "202701")
    payload = json.loads(out)

    assert code == 0
    assert payload["verdicts"] == {"identical": "PASS", "course_level_invariant": "PASS"}
    assert payload["changed"] == 0
    assert payload["float_noise"]["tolerance"] == SCORE_TOLERANCE
    assert payload["float_noise"]["count"] == 1
    assert payload["float_noise"]["max_abs_delta"] == pytest.approx(1e-12, rel=0.1)


def test_script_exit_1_when_stored_cache_differs_just_beyond_tolerance(
    file_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with Session(file_engine) as session:
        _seed_term(session)
    _tamper_stored_easiness(file_engine, "70001", 2e-9)

    code, out = _run_main(monkeypatch, capsys, file_engine, "--term", "202701")
    payload = json.loads(out)

    assert code == 1
    assert payload["verdicts"] == {"identical": "FAIL", "course_level_invariant": "FAIL"}
    assert [record["crn"] for record in payload["course_level_violations"]] == ["70001"]
    assert payload["float_noise"]["count"] == 0


def test_script_exit_1_on_a_label_change_alongside_noise(
    file_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with Session(file_engine) as session:
        _seed_term(session)
        cache_row = session.scalars(
            select(SectionRankingCache).where(SectionRankingCache.crn == "70001")
        ).one()
        cache_row.easiness_score = cache_row.easiness_score + 1e-12
        cache_row.confidence_label = "changed-label"
        session.commit()

    code, out = _run_main(monkeypatch, capsys, file_engine, "--term", "202701")
    payload = json.loads(out)

    assert code == 1
    assert payload["changed"] == 1
    assert payload["float_noise"]["count"] == 1


def test_script_never_writes(
    file_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with Session(file_engine) as session:
        _seed_term(session)
        before = [
            (row.id, row.refreshed_at, row.easiness_score)
            for row in session.scalars(select(SectionRankingCache).order_by(SectionRankingCache.id))
        ]

    _run_main(monkeypatch, capsys, file_engine, "--term", "202701")

    with Session(file_engine) as session:
        after = [
            (row.id, row.refreshed_at, row.easiness_score)
            for row in session.scalars(select(SectionRankingCache).order_by(SectionRankingCache.id))
        ]
    assert before == after


def test_script_exit_3_when_database_unreachable(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    # An engine whose database file cannot be opened: SQLAlchemy raises OperationalError.
    unreachable = create_engine(f"sqlite+pysqlite:///{tmp_path / 'missing' / 'nope.sqlite3'}")

    def failing(*_args: Any, **_kwargs: Any) -> Any:
        raise OperationalError("select", {}, Exception("secret://host"))

    monkeypatch.setattr(report, "get_engine", lambda: unreachable)
    monkeypatch.setattr(report, "collect_diff", failing)

    code = report.main(["--term", "202701"])
    out = capsys.readouterr().out

    payload = json.loads(out)
    assert code == 3
    assert payload["verdicts"] == {
        "identical": "NOT MEASURED",
        "course_level_invariant": "NOT MEASURED",
    }
    assert "://" not in out


def test_script_help_lists_options(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        report.main(["--help"])

    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    for option in ("--term", "--top", "--report-json"):
        assert option in out


def test_script_requires_term() -> None:
    with pytest.raises(SystemExit) as excinfo:
        report.main([])

    assert excinfo.value.code != 0
