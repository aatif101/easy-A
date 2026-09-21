# Deferred Items — Phase 04 Plan 01

Out-of-scope issues discovered during execution of `04-01-PLAN.md`. Not fixed here per the
scope-boundary rule (only issues directly caused by this plan's changes are auto-fixed).

## Pre-existing strict-mypy failures in `tests/test_database_config.py`

Discovered running `uv run mypy src migrations scripts tests` after Task 2. Confirmed via
`git diff --stat HEAD -- tests/test_database_config.py` (no diff) and `git log -1 -- tests/test_database_config.py`
(commit `106a06d`, unrelated to Phase 04) that this file is untouched by 04-01.

```
tests/test_database_config.py:14: error: Argument 2 to "Settings" has incompatible type "**dict[str, str | None]"; expected "str"  [arg-type]
tests/test_database_config.py:14: error: Argument 2 to "Settings" has incompatible type "**dict[str, str | None]"; expected "int"  [arg-type]
tests/test_database_config.py:14: error: Argument 2 to "Settings" has incompatible type "**dict[str, str | None]"; expected "bool"  [arg-type]
tests/test_database_config.py:49: error: Unused "type: ignore" comment  [unused-ignore]
tests/test_database_config.py:56: error: Unused "type: ignore" comment  [unused-ignore]
```

Not in `04-01-PLAN.md` `files_modified`. Ruff and the full pytest suite (`uv run pytest -q`,
257 passed / 3 skipped) are unaffected — this is a strict-mypy-only finding in an unrelated file.
