# All-Tampa Section Ingestion Runbook

Use this runbook to run the full-scale, resumable, paced ingestion of the Tampa Spring 2027 course/section universe (~1,402 courses / ~3,782 sections across ~212 subjects) into the live hosted Supabase database, via `scripts/refresh_all_tampa.py`.

The orchestrator drives the existing, unmodified `scripts/refresh_course_coverage.py` once per subject. Each subject is its own OS process and its own database transaction, so a single subject's failure cannot discard another subject's already-committed work (06-RESEARCH.md Pitfall 1). No production ingestion code (`src/easy_a/refresh/coverage.py`, `src/easy_a/refresh/target_cli.py`) is touched by this runbook or the orchestrator.

## Preconditions

- `EASY_A_DATABASE_URL` (hosted Supabase) is configured — the only live database (see `.planning/STATE.md`).
- `config/course_targets.toml` is the full generated ~1,402-entry target list (committed by 06-01). Regenerate it with `scripts/generate_tampa_targets.py` if it has drifted from `courses.csv`.
- `courses.csv` freshness: the enumeration snapshot behind the committed target list is dated 2026-09-20 (06-RESEARCH.md Assumption A2). Before a full run, either re-verify it against the current USF Tampa Spring 2027 schedule, or explicitly accept the dated snapshot as the basis for this run — record which decision was made in the Run Log below.
- This is purely additive, idempotent upsert ingestion (no deletes). Re-running a subject that already completed is a no-op.

## 1. (Re)generate the target list, if needed

```bash
uv run python scripts/generate_tampa_targets.py --csv courses.csv --out config/course_targets.toml
```

Skip this step if `config/course_targets.toml` is already current — 06-01 already committed the full ~1,402-entry list.

## 2. Run the full-scale ingestion

```bash
uv run python scripts/refresh_all_tampa.py \
  --term 202701 \
  --targets config/course_targets.toml \
  --pace-seconds 2
```

This enumerates the distinct subjects present in `--targets` (sorted), and invokes:

```bash
uv run python scripts/refresh_course_coverage.py --term 202701 --targets config/course_targets.toml --subject <SUBJ>
```

once per subject, each in its own subprocess/transaction. A progress file (default `refresh_all_tampa.progress` in the working directory; override with `--progress`) records each subject immediately after it completes successfully (exit code 0). The orchestrator itself never opens a database session or imports `refresh_targets` directly.

## Pacing rationale

`--pace-seconds` (default `2.0`) is a deliberate delay applied *between* subject invocations — never before the first, and never inside an individual request. This mirrors the 10-course pilot's own precedent (`phase1_report.md`: "sequential subject searches with two-second pauses") and keeps the full run within the spirit of D-08/D-09's bounded, narrow-request posture, even though the total request volume at full scale (~2,800 requests) is far higher than any prior run.

Do not remove or shorten the pacing without an explicit operator decision. Raising `--pace-seconds` is always safe if USF-side throttling (HTTP 429/503, or unusually slow responses) is observed mid-run.

## Resume-after-failure procedure

If a subject invocation exits non-zero (USF 429/503/timeout, a transient network failure, or an unexpected parse error), the orchestrator:

1. Records that subject in the failed list for this run.
2. Does **not** mark it completed in the progress file.
3. Continues on to the next subject — it does not abort the whole run.

The final summary line lists every failed subject by name. To resume and retry only the not-yet-completed subjects, re-invoke the exact same command:

```bash
uv run python scripts/refresh_all_tampa.py \
  --term 202701 \
  --targets config/course_targets.toml \
  --pace-seconds 2 \
  --progress refresh_all_tampa.progress
```

The orchestrator re-reads the progress file, skips every subject already recorded there (reported as "Already done (skipped)"), and only re-attempts subjects that were never recorded (including any previously-failed subjects). Repeat this resume command until the final summary reports `Failed: 0`.

## Post-run verification

After the orchestrator reports 0 failed subjects, verify against the existing quality tooling (06-03 performs the complete post-run validation pass; the pointers below are the minimal check):

```bash
uv run python scripts/check_data_quality.py --term 202701 --json
```

Expect 0 errors, and a section count on the order of ~3,782 (far above the 132-section pilot baseline). See `06-03-PLAN.md` for the full validation checklist (config/stored-data reconciliation, suffix-guard spot-checks across more base courses, section-rankings cache state, and API-level agreement).

## Run Log

Record the final measured, dated course/section counts here after each full run, per the project's measured-and-dated convention (D-06/D-07):

| Date | Operator decision (courses.csv freshness / pacing) | Courses | Sections | Quality errors |
|------|------------------------------------------------------|---------|----------|-----------------|
| _pending_ | _pending Task 2 operator approval_ | — | — | — |
