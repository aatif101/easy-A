from __future__ import annotations

from dataclasses import replace

from easy_a.sync.gate import GateInput, evaluate_gate

SUBJECTS = frozenset(f"S{i:02d}" for i in range(100))


def _base(**overrides: object) -> GateInput:
    base = GateInput(
        in_scope_rows=3700,
        db_active_in_scope=1000,
        missing_active=0,
        last_success_records_seen=3700,
        db_active_subjects=SUBJECTS,
        sweep_subjects=SUBJECTS,
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


def test_clean_sweep_passes() -> None:
    result = evaluate_gate(_base())
    assert result.passed is True
    assert result.reasons == ()


def test_empty_sweep_fails_with_zero_rows() -> None:
    result = evaluate_gate(_base(in_scope_rows=0, last_success_records_seen=None))
    assert result.passed is False
    assert "zero_rows" in result.reasons


def test_missing_fraction_passes_at_threshold_and_fails_just_over() -> None:
    assert evaluate_gate(_base(missing_active=100)).passed is True
    over = evaluate_gate(_base(missing_active=101))
    assert over.passed is False
    assert over.reasons[0].startswith("missing_fraction 0.101 above 0.100")


def test_missing_fraction_skipped_when_database_has_no_active_sections() -> None:
    result = evaluate_gate(_base(db_active_in_scope=0, missing_active=0))
    assert result.passed is True


def test_row_floor_passes_at_ninety_percent_and_fails_just_under() -> None:
    assert evaluate_gate(_base(in_scope_rows=3330)).passed is True
    under = evaluate_gate(_base(in_scope_rows=3329))
    assert under.passed is False
    assert under.reasons == ("row_floor 3329 below 90% of 3700",)


def test_row_floor_skipped_without_a_prior_success() -> None:
    result = evaluate_gate(_base(in_scope_rows=10, last_success_records_seen=None))
    assert result.passed is True


def test_absent_subjects_pass_at_limit_and_fail_just_over() -> None:
    # 100 subjects: limit is max(2, floor(0.02 * 100)) = 2.
    at_limit = frozenset(sorted(SUBJECTS)[2:])
    assert evaluate_gate(_base(sweep_subjects=at_limit)).passed is True
    over = frozenset(sorted(SUBJECTS)[3:])
    result = evaluate_gate(_base(sweep_subjects=over))
    assert result.passed is False
    assert result.reasons == ("subjects_absent 3 above 2: S00, S01, S02",)


def test_absent_subject_limit_scales_with_subject_count() -> None:
    many = frozenset(f"T{i:03d}" for i in range(300))  # floor(0.02 * 300) = 6
    six_absent = frozenset(sorted(many)[6:])
    seven_absent = frozenset(sorted(many)[7:])
    assert evaluate_gate(_base(db_active_subjects=many, sweep_subjects=six_absent)).passed is True
    assert (
        evaluate_gate(_base(db_active_subjects=many, sweep_subjects=seven_absent)).passed is False
    )


def test_many_additions_never_fail() -> None:
    extra = SUBJECTS | frozenset({"NEW1", "NEW2"})
    result = evaluate_gate(
        _base(in_scope_rows=5200, last_success_records_seen=3700, sweep_subjects=extra)
    )
    assert result.passed is True


def test_first_sweep_with_known_catch_up_passes() -> None:
    # Research measurement: 104 missing of 3,783 active sections is 2.7 percent.
    result = evaluate_gate(
        _base(
            in_scope_rows=3700,
            db_active_in_scope=3783,
            missing_active=104,
            last_success_records_seen=None,
        )
    )
    assert result.passed is True


def test_all_failed_rules_are_reported_together() -> None:
    result = evaluate_gate(
        _base(
            in_scope_rows=1000,
            missing_active=500,
            sweep_subjects=frozenset(sorted(SUBJECTS)[:10]),
        )
    )
    assert result.passed is False
    assert len(result.reasons) == 3
