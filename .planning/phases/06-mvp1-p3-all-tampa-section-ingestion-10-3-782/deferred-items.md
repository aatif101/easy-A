# Deferred items — Phase 06 (MVP1-P3)

Out-of-scope discoveries noticed during execution but not fixed, per the executor's scope
boundary (only auto-fix issues directly caused by the current task's changes).

## 06-01

- `src/easy_a/refresh/cleanup.py:492-496` (`_dependent_ids` signature) — pre-existing ruff
  `E501` (line too long, 101 > 100 chars). Confirmed pre-existing (present before this plan's
  changes, at the un-shifted line number) via inspection of the pre-change file content —
  unrelated to the `_target_filter` fix in this plan. Not fixed here.
- `tests/test_database_config.py:14,49,56` — pre-existing `mypy` errors (`arg-type` on
  `Settings(**dict[str, str | None])`, two `unused-ignore` comments). Confirmed pre-existing by
  running `uv run mypy tests/test_database_config.py` in isolation, with no `scripts/`
  involvement — unrelated to this plan's `scripts/generate_tampa_targets.py` addition or the
  `scripts/__init__.py` fix. Not fixed here.
