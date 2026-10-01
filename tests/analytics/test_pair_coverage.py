from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from easy_a.analytics import pair_coverage
from easy_a.analytics.pair_coverage import (
    REFERENCE_2026_09_28,
    PairCoverage,
    measure_instructor_pairs,
)
from easy_a.db import Base
from easy_a.models import Course, GradeDistribution, Section, SectionInstructor, Term

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts/measure_instructor_pairs.py"
_spec = importlib.util.spec_from_file_location("measure_instructor_pairs", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
script = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = script
_spec.loader.exec_module(script)

OBSERVED_AT = datetime(2026, 9, 20, 12, tzinfo=UTC)

TERM_SPRING_2027 = 1
TERM_FALL_2024 = 2
TERM_SPRING_2025 = 3

# Names used in the seeded data; none may ever appear in the tool's output.
SEEDED_NAMES = ("A. One", "B. Two", "Staff")


def _create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                Term(id=1, banner_code="202701", name="Spring 2027", year=2027, season="Spring"),
                Term(id=2, banner_code="202408", name="Fall 2024", year=2024, season="Fall"),
                Term(id=3, banner_code="202501", name="Spring 2025", year=2025, season="Spring"),
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
            ]
        )
        session.commit()


@pytest.fixture
def engine(tmp_path: Path) -> Generator[Engine, None, None]:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'pairs.sqlite3'}")
    _create_schema(engine)
    yield engine
    engine.dispose()


def _grade(
    session: Session,
    *,
    term_id: int,
    crn: str,
    course_id: int | None = 10,
    a: int = 0,
    b: int = 0,
    c: int = 0,
    d: int = 0,
    f: int = 0,
    w: int = 0,
    total: int | None = None,
) -> None:
    session.add(
        GradeDistribution(
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
            s_count=0,
            u_count=0,
            w_count=w,
            other_count=0,
            total_grades=a + b + c + d + f + w if total is None else total,
            source=f"pairs-{term_id}-{crn}",
            source_hash="pairs",
        )
    )


def _section(
    session: Session,
    *,
    term_id: int,
    crn: str,
    course_id: int = 10,
    names: tuple[str, ...] = (),
    section_type: str = "Class Lecture",
) -> None:
    section = Section(
        term_id=term_id,
        crn=crn,
        course_id=course_id,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type=section_type,
        primary_status="Active",
        first_seen_at=OBSERVED_AT,
        last_seen_at=OBSERVED_AT,
    )
    session.add(section)
    session.flush()
    for name in names:
        session.add(
            SectionInstructor(
                section_id=section.id,
                name_raw=name,
                name_normalized=name.lower(),
                source="pairs-test",
                observed_at=OBSERVED_AT,
            )
        )


def _seed_example(session: Session) -> None:
    _section(session, term_id=TERM_FALL_2024, crn="10001", names=("A. One",))
    _grade(session, term_id=TERM_FALL_2024, crn="10001", a=30, b=10)
    _section(session, term_id=TERM_SPRING_2025, crn="10002", names=("A. One",))
    _grade(session, term_id=TERM_SPRING_2025, crn="10002", a=20, b=10)
    _section(session, term_id=TERM_SPRING_2025, crn="10003", names=("B. Two",))
    _grade(session, term_id=TERM_SPRING_2025, crn="10003", a=5, b=5)
    _section(session, term_id=TERM_SPRING_2025, crn="10004", course_id=11, names=("Staff",))
    _grade(session, term_id=TERM_SPRING_2025, crn="10004", course_id=11, a=20)
    _grade(session, term_id=TERM_SPRING_2025, crn="99999", a=7)
    session.commit()


def test_seeded_example_matches_the_behavior_table(engine: Engine) -> None:
    with Session(engine) as session:
        _seed_example(session)
        coverage = measure_instructor_pairs(session, before_term="202701")

    assert coverage.pairs_total == 2
    assert coverage.n_ge_60 == 1
    assert coverage.n_ge_30 == 1
    assert coverage.n_ge_15 == 1
    assert coverage.n_ge_5 == 2
    assert coverage.n_ge_1 == 2
    assert coverage.multi_term_pairs == 1
    assert coverage.n_ge_30_multi_term == 1
    assert coverage.term_span == {"1": 1, "2": 1}
    assert coverage.grade_rows_total == 5
    assert coverage.grade_rows_with_section == 4
    assert coverage.grade_rows_named == 3
    assert coverage.grade_rows_staff_or_blank == 1
    assert coverage.instructors == 2
    assert coverage.courses == 1
    assert coverage.before_term == "202701"


def test_same_name_in_two_courses_is_two_pairs_one_instructor(engine: Engine) -> None:
    with Session(engine) as session:
        _section(session, term_id=TERM_SPRING_2025, crn="20001", course_id=10, names=("A. One",))
        _grade(session, term_id=TERM_SPRING_2025, crn="20001", a=10)
        _section(session, term_id=TERM_SPRING_2025, crn="20002", course_id=11, names=("A. One",))
        _grade(session, term_id=TERM_SPRING_2025, crn="20002", course_id=11, a=10)
        session.commit()

        coverage = measure_instructor_pairs(session, before_term="202701")

    assert (coverage.pairs_total, coverage.instructors, coverage.courses) == (2, 1, 2)


def test_name_case_and_spacing_do_not_split_an_instructor(engine: Engine) -> None:
    with Session(engine) as session:
        _section(session, term_id=TERM_FALL_2024, crn="21001", names=("A.  One",))
        _grade(session, term_id=TERM_FALL_2024, crn="21001", a=10)
        _section(session, term_id=TERM_SPRING_2025, crn="21002", names=("a. one ",))
        _grade(session, term_id=TERM_SPRING_2025, crn="21002", a=10)
        session.commit()

        coverage = measure_instructor_pairs(session, before_term="202701")

    assert (coverage.pairs_total, coverage.instructors, coverage.term_span) == (1, 1, {"2": 1})


def test_duplicate_name_rows_on_one_section_count_once(engine: Engine) -> None:
    with Session(engine) as session:
        _section(
            session,
            term_id=TERM_SPRING_2025,
            crn="22001",
            names=("A. One", "A. One", "a. one"),
        )
        _grade(session, term_id=TERM_SPRING_2025, crn="22001", a=40)
        session.commit()

        coverage = measure_instructor_pairs(session, before_term="202701")

    assert coverage.pairs_total == 1
    assert coverage.n_ge_30 == 1
    assert coverage.n_ge_60 == 0


def test_co_taught_section_credits_each_instructor_and_counts_one_named_row(
    engine: Engine,
) -> None:
    with Session(engine) as session:
        _section(session, term_id=TERM_SPRING_2025, crn="23001", names=("A. One", "B. Two"))
        _grade(session, term_id=TERM_SPRING_2025, crn="23001", a=40)
        session.commit()

        coverage = measure_instructor_pairs(session, before_term="202701")

    assert coverage.pairs_total == 2
    assert coverage.grade_rows_named == 1


def test_effective_n_is_min_of_letter_grades_and_total(engine: Engine) -> None:
    with Session(engine) as session:
        # A-F = 30 but the total is 50 (withdrawals): the pair's n is 30, not 50.
        _section(session, term_id=TERM_SPRING_2025, crn="24001", names=("A. One",))
        _grade(session, term_id=TERM_SPRING_2025, crn="24001", a=30, w=20)
        # A-F = 30 exceeds a (corrupt) total of 20: n is 20.
        _section(session, term_id=TERM_SPRING_2025, crn="24002", course_id=11, names=("B. Two",))
        _grade(session, term_id=TERM_SPRING_2025, crn="24002", course_id=11, a=30, total=20)
        session.commit()

        coverage = measure_instructor_pairs(session, before_term="202701")

    assert coverage.pairs_total == 2
    assert coverage.n_ge_30 == 1
    assert coverage.n_ge_15 == 2
    assert coverage.n_ge_5 == 2


def test_rows_of_terms_at_or_after_before_term_are_excluded(engine: Engine) -> None:
    with Session(engine) as session:
        _section(session, term_id=TERM_FALL_2024, crn="25001", names=("A. One",))
        _grade(session, term_id=TERM_FALL_2024, crn="25001", a=10)
        _section(session, term_id=TERM_SPRING_2025, crn="25002", names=("A. One",))
        _grade(session, term_id=TERM_SPRING_2025, crn="25002", a=10)
        _section(session, term_id=TERM_SPRING_2027, crn="25003", names=("A. One",))
        _grade(session, term_id=TERM_SPRING_2027, crn="25003", a=10)
        session.commit()

        through_2027 = measure_instructor_pairs(session, before_term="202701")
        before_2025 = measure_instructor_pairs(session, before_term="202501")
        before_2024 = measure_instructor_pairs(session, before_term="202408")

    assert through_2027.grade_rows_total == 2
    assert through_2027.term_span == {"2": 1}
    assert before_2025.grade_rows_total == 1
    assert before_2025.term_span == {"1": 1}
    assert before_2024.grade_rows_total == 0
    assert before_2024.pairs_total == 0


def test_blank_and_staff_names_are_excluded_case_insensitively(engine: Engine) -> None:
    with Session(engine) as session:
        _section(session, term_id=TERM_SPRING_2025, crn="26001", names=("  STAFF ",))
        _grade(session, term_id=TERM_SPRING_2025, crn="26001", a=10)
        _section(session, term_id=TERM_SPRING_2025, crn="26002", names=("   ",))
        _grade(session, term_id=TERM_SPRING_2025, crn="26002", a=10)
        _section(session, term_id=TERM_SPRING_2025, crn="26003", names=())
        _grade(session, term_id=TERM_SPRING_2025, crn="26003", a=10)
        session.commit()

        coverage = measure_instructor_pairs(session, before_term="202701")

    assert coverage.pairs_total == 0
    assert coverage.grade_rows_with_section == 3
    assert coverage.grade_rows_named == 0
    assert coverage.grade_rows_staff_or_blank == 3


def test_section_type_histogram_counts_grade_rows_with_a_section(engine: Engine) -> None:
    with Session(engine) as session:
        _section(
            session,
            term_id=TERM_SPRING_2025,
            crn="27001",
            names=("A. One",),
            section_type="Laboratory",
        )
        _grade(session, term_id=TERM_SPRING_2025, crn="27001", a=10)
        _section(session, term_id=TERM_SPRING_2025, crn="27002", names=("A. One",))
        _grade(session, term_id=TERM_SPRING_2025, crn="27002", a=10)
        _section(session, term_id=TERM_FALL_2024, crn="27003", names=("A. One",))
        _grade(session, term_id=TERM_FALL_2024, crn="27003", a=10)
        _grade(session, term_id=TERM_FALL_2024, crn="27999", a=10)
        session.commit()

        coverage = measure_instructor_pairs(session, before_term="202701")

    assert coverage.section_type_histogram == {"Class Lecture": 2, "Laboratory": 1}
    # The raw join counts laboratory sections: the lab rule is the ranking diff's concern.
    assert coverage.pairs_total == 1
    assert coverage.n_ge_30 == 1


def test_matches_reference_requires_four_headline_numbers() -> None:
    def coverage(**overrides: Any) -> PairCoverage:
        values: dict[str, Any] = {
            "before_term": "202701",
            "pairs_total": 3216,
            "n_ge_60": 1329,
            "n_ge_30": 2178,
            "n_ge_15": 2829,
            "n_ge_5": 3208,
            "n_ge_1": 3216,
            "instructors": 1796,
            "courses": 1117,
            "multi_term_pairs": 1439,
            "n_ge_30_multi_term": 1308,
            "term_span": {"1": 1777, "2": 965, "3": 359, "4": 110, "5": 5},
            "grade_rows_total": 8662,
            "grade_rows_with_section": 8662,
            "grade_rows_named": 8661,
            "grade_rows_staff_or_blank": 1,
            "section_type_histogram": {},
            "reference": dict(REFERENCE_2026_09_28),
        }
        values.update(overrides)
        return PairCoverage(**values)

    exact = coverage()
    assert exact.matches_reference
    assert all(delta == 0 for key, delta in exact.deltas.items() if key != "term_span")
    assert set(exact.deltas["term_span"].values()) == {0}

    for field_name in ("pairs_total", "n_ge_60", "n_ge_30", "n_ge_15"):
        assert not coverage(**{field_name: 1}).matches_reference

    # The other reference numbers do not gate the match, but still show up as deltas.
    off = coverage(n_ge_5=3200, instructors=1790, term_span={"1": 1780, "6": 2})
    assert off.matches_reference
    assert off.deltas["n_ge_5"] == -8
    assert off.deltas["instructors"] == -6
    assert off.deltas["term_span"]["1"] == 3
    assert off.deltas["term_span"]["2"] == -965
    assert off.deltas["term_span"]["6"] == 2
    assert list(off.deltas["term_span"]) == ["1", "2", "3", "4", "5", "6"]


def test_reference_holds_the_2026_09_28_numbers() -> None:
    assert REFERENCE_2026_09_28["pairs"] == 3216
    assert (
        REFERENCE_2026_09_28["n_ge_60"],
        REFERENCE_2026_09_28["n_ge_30"],
        REFERENCE_2026_09_28["n_ge_15"],
        REFERENCE_2026_09_28["n_ge_5"],
        REFERENCE_2026_09_28["n_ge_1"],
    ) == (1329, 2178, 2829, 3208, 3216)
    assert REFERENCE_2026_09_28["term_span"] == {
        "1": 1777,
        "2": 965,
        "3": 359,
        "4": 110,
        "5": 5,
    }


def test_deltas_are_after_minus_reference(engine: Engine) -> None:
    with Session(engine) as session:
        _seed_example(session)
        coverage = measure_instructor_pairs(session, before_term="202701")

    assert not coverage.matches_reference
    assert coverage.deltas["pairs"] == 2 - 3216
    assert coverage.deltas["n_ge_60"] == 1 - 1329
    assert coverage.deltas["grade_rows_total"] == 5 - 8662
    assert coverage.deltas["term_span"]["1"] == 1 - 1777
    assert set(coverage.deltas) == set(REFERENCE_2026_09_28)


# --- script ---------------------------------------------------------------------------------


def _run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    engine: Engine,
    *argv: str,
) -> tuple[int, str]:
    monkeypatch.setattr(script, "get_engine", lambda: engine)
    code = script.main(list(argv))
    return code, capsys.readouterr().out


def test_script_exit_1_when_the_database_differs_from_the_report(
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    with Session(engine) as session:
        _seed_example(session)

    report_path = tmp_path / "reports" / "pairs.json"
    code, out = _run(monkeypatch, capsys, engine, "--report-json", str(report_path))

    payload = json.loads(out)
    assert code == 1
    assert payload["verdict"] == "FAIL"
    assert payload["matches_reference"] is False
    assert payload["pairs_total"] == 2
    assert payload["before_term"] == "202701"
    assert json.loads(report_path.read_text(encoding="utf-8")) == payload
    assert "://" not in out
    for name in SEEDED_NAMES:
        assert name not in out


def test_script_exit_0_when_numbers_match_a_patched_reference(
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with Session(engine) as session:
        _seed_example(session)
    monkeypatch.setattr(
        pair_coverage,
        "REFERENCE_2026_09_28",
        {
            "pairs": 2,
            "n_ge_60": 1,
            "n_ge_30": 1,
            "n_ge_15": 1,
            "n_ge_5": 2,
            "n_ge_1": 2,
            "term_span": {"1": 1, "2": 1},
        },
    )

    code, out = _run(monkeypatch, capsys, engine, "--before-term", "202701")

    payload = json.loads(out)
    assert code == 0
    assert payload["verdict"] == "PASS"
    assert payload["matches_reference"] is True
    assert payload["deltas"] == {
        "pairs": 0,
        "n_ge_60": 0,
        "n_ge_30": 0,
        "n_ge_15": 0,
        "n_ge_5": 0,
        "n_ge_1": 0,
        "term_span": {"1": 0, "2": 0},
    }


def test_script_never_writes(
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with Session(engine) as session:
        _seed_example(session)
        counts_before = _row_counts(session)

    _run(monkeypatch, capsys, engine)

    with Session(engine) as session:
        assert _row_counts(session) == counts_before


def _row_counts(session: Session) -> tuple[int, int, int]:
    return (
        session.query(GradeDistribution).count(),
        session.query(Section).count(),
        session.query(SectionInstructor).count(),
    )


def test_script_exit_3_when_database_unreachable(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    unreachable = create_engine(f"sqlite+pysqlite:///{tmp_path / 'missing' / 'nope.sqlite3'}")

    def failing(*_args: Any, **_kwargs: Any) -> Any:
        raise OperationalError("select", {}, Exception("secret://host"))

    monkeypatch.setattr(script, "get_engine", lambda: unreachable)
    monkeypatch.setattr(script, "collect_pair_coverage", failing)

    code = script.main([])
    out = capsys.readouterr().out

    payload = json.loads(out)
    assert code == 3
    assert payload["verdict"] == "NOT MEASURED"
    assert "://" not in out


def test_script_help_lists_options(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        script.main(["--help"])

    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "--before-term" in out
    assert "--report-json" in out
