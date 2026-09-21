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

## Pre-existing ruff E501 in `src/easy_a/refresh/cleanup.py`

Discovered during `04-02-PLAN.md` execution running `uv run ruff check .` (full-repo gate). Confirmed
via `git log -1 -- src/easy_a/refresh/cleanup.py` (last touched at commit `0c0f0c9`, 2026-09-20,
predating this plan's commits `d45fda9`/`1dac70d`) that this file is untouched by 04-02.

```
E501 Line too long (101 > 100)
   --> src/easy_a/refresh/cleanup.py:494:101
```

Not in `04-02-PLAN.md` `files_modified` (`src/easy_a/grades/parser.py`, `tests/grades/test_parser.py`,
`src/easy_a/quality/checks.py`, `tests/quality/test_checks.py`). `uv run ruff check` on this plan's
changed files passes clean; the full pytest suite (`uv run pytest -q`, 261 passed / 3 skipped) is
unaffected.
