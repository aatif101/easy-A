# Phase 10 Gap 01: float tolerance in the ranking-diff comparison

Decision: "revise-with-tolerance" (user), after plan 10-07's D-03 code-only parity gate returned exit 1 on live 202701 data (see `10-ROLLOUT-EVIDENCE.md`).

## Why

The stored `section_rankings` cache and a local recomputation differ by float noise only: 3,667 of 3,703 CRNs, max abs easiness delta 5.33e-15, no `score_source`/`effective_n`/`confidence_label` change, rank shift 0. Recomputing with `origin/main` code and with this branch's code gives identical results, so the gap pre-exists Phase 10. The exact-equality comparison could never pass against this cache.

## What changed

- `src/easy_a/rankings/diff.py`: new `SCORE_TOLERANCE = 1e-9` and `FLOAT_SCORE_FIELDS` (`easiness_score`, `smoothed_withdrawal_rate`); `float_differs` / `changed_score_fields` are the one shared comparison. `diff_score_rows` uses it, so `identical` and `course_level_invariant` are tolerant everywhere they are consumed. All other fields (`effective_n`, `confidence_label`, `score_source`, CRN identity) stay exact. NaN is never treated as noise.
- Rank: `identical` now also requires `rank_shift.max == 0`. With exact comparison a rank could not move without a score change; with a tolerance it could (noise reordering near-ties), and that must still fail. `course_level_invariant` is unchanged (rank is not part of it).
- Noise stays visible: every diff object (`to_dict`) now carries `float_noise: {tolerance, count, max_abs_delta}` (count = sections with a within-tolerance float-field difference; max = largest such difference over both float fields).
- Gates: `scripts/report_ranking_diff.py` (exit 0 when all within tolerance, 1 otherwise) and the dry-run `code_only_parity` / `course_level_invariant` and the `--apply` `course_level_invariant` gate in `src/easy_a/schedule/backfill_cli.py` already consumed `RankingDiff.identical` / `.course_level_invariant`, so they inherit the tolerance with no separate comparison code (`backfill.py` has none). Only docstrings and help text changed there.
- `docs/runbooks/historical-instructor-backfill.md`: states the tolerance, why, and how to read `float_noise`.

## Tests

- `tests/rankings/test_diff.py`: within-tolerance (both fields, both signs, exactly at tolerance) passes and is counted; just beyond (2e-9) fails and is a course-level violation; noise does not mask a real change on the other field; per-section noise count and max across fields; `effective_n`/label/source stay exact; NaN fails; noise-only rank flip is not identical; missing/extra CRN still fail; script exit 0 on 1e-12 noise, exit 1 on 2e-9, exit 1 on label change alongside noise.
- `tests/schedule/test_backfill_cli.py`: dry run passes both gates with 1e-12 stored noise and reports `float_noise`; fails both with 2e-9; `--apply` commits with noise and reports it, and rolls back (nothing written) with a 2e-9 course-level difference.
- Existing assertions on real differences are unchanged.

## Results (local only; no hosted DB or USF access)

- `uv run pytest -q`: 868 passed, 4 skipped, 1 warning (was 843 passed, 4 skipped)
- `uv run ruff check .`: all checks passed
- `uv run mypy src`: no issues in 92 source files

## Next

Re-run the D-03 parity gate against hosted data (read-only) and then the dry run, per plan 10-07. Not done here.
