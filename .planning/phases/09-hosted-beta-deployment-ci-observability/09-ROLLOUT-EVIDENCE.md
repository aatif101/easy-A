# Phase 9 Rollout Evidence (plan 09-14)

Dated evidence for the pre-deploy half of the hosted rollout. No connection strings, hostnames or credentials appear in this file. All database checks below ran inside READ ONLY transactions.

## Migration 0004

Applied to hosted Supabase by the operator (Task 1 of plan 09-14, blocking-human gate). The operator ran the upgrade from their own shell; the executor did not apply or re-apply anything. The orchestrator then ran the read-only verification below.

Verification time: 2026-09-30T05:14:52+00:00 (UTC).

| Check | Result |
|-------|--------|
| `alembic_version` | `0004_sync_removed_at` (head) |
| `sections.removed_at` | `timestamp with time zone`, nullable = YES |
| Index `ix_seat_snapshots_section_id_observed_at` | present |
| `count(*) FROM sections WHERE removed_at IS NOT NULL` | 0 |

Branch state before the rollout: `codex/render-setup` was merged with a freshly fetched `origin/main` first (merge commit `d99a206`, no file changes), so the branch descends from `origin/main` (PROJECT.md D-10).

## Real-data dry run

Command: `/usr/bin/time -v uv run python -m easy_a.sync --term 202701 --dry-run`, executed exactly once (one USF request; not repeated in this plan).

| Item | Value |
|------|-------|
| Shell start (UTC) | 2026-09-30T05:15:44Z |
| Sweep `started_at` (UTC, from the JSON line) | 2026-09-30T05:15:45.689Z |
| Shell end (UTC) | 2026-09-30T05:16:01Z |
| Commit SHA | `d99a206c20dbd742d58164d5d012799c10c8c9b6` |
| Exit code | 0 |
| Event | `sweep_dry_run` |
| Gate result | passed (`gate_reasons` empty) |
| Bytes | 7,103,329 |
| Content-Encoding | none reported (`null`); the response was not compressed |
| Sweep duration | 15.209 s (wall clock including start-up, per `/usr/bin/time`: 17.15 s) |
| `tail_error` | true (the known USF error tail after the last row; not a failure, see 09-RESEARCH.md Pitfall 1) |
| `error_kind` / `error_detail` | null / null |
| stderr | empty |

### D-03 scope breakdown

| Field | Value |
|-------|-------|
| total_rows | 6,645 |
| distinct_crns | 6,645 |
| non_tampa_rows | 0 |
| graduate_rows | 2,941 |
| unparseable_number_rows | 0 |
| in_scope_rows | 3,704 |
| subjects (in scope) | 210 |
| course_keys (in scope) | 1,372 |

Arithmetic check: 6,645 total - 0 non-Tampa - 2,941 graduate - 0 unparseable = 3,704 in scope.

### Expected catch-up (what a real sweep would do)

| Item | Count |
|------|-------|
| inserted (new CRNs in already-tracked courses) | 12 |
| updated (distinct sections with any change) | 543 |
| removed | 105 |
| restored | 0 |
| instructor_changes | 150 |
| seat_changes | 97 |
| auto_added | 0 (dry run adds nothing) |
| unapplied courses | 0 |

Would-add courses (13, by name): ARH 4301, ART 3781C, ART 4930, FIL 4839, FIN 4934, HUM 4368, HUM 4391, HUM 4434, HUM 4890, LDR 3363, LDR 4204, NEB 0001, POT 4936.

Removal share: 105 of 3,783 active sections is 2.8 percent, under the 10 percent gate.

### Memory

| Measure | Value | Against 350 MB target | Against 512 MB plan limit |
|---------|-------|-----------------------|---------------------------|
| `peak_rss_mb` from the JSON log line | 228.0 MiB | under (65 percent) | under (44.5 percent) |
| `/usr/bin/time -v` Maximum resident set size | 233,428 kB (about 228.0 MiB) | under | under |

The two measures agree. The figure covers the whole dry run (imports, fetch, chunked parse, database staging, diff), not only the parse.

### A2 outcome (idle-in-transaction)

No termination occurred. The dry run opens a transaction, takes the advisory sweep lock first, sets READ ONLY, and holds that transaction across the roughly 15 second USF fetch, which is the same shape as a real sweep. It completed with exit 0, empty stderr and no "idle-in-transaction" or "terminating connection" text anywhere in the output. Assumption A2 held for this path. A writing sweep is not exercised here (this plan must not run one), so the first hosted worker sweep remains the final confirmation.

## Row counts before/after

Captured in READ ONLY transactions immediately before and after the single dry run.

| Table / filter | Before (2026-09-30T05:15:36Z) | After (2026-09-30T05:16:06Z) | Identical |
|----------------|-------------------------------|------------------------------|-----------|
| sections | 3,783 | 3,783 | yes |
| sections with removed_at set | 0 | 0 | yes |
| section_instructors | 4,226 | 4,226 | yes |
| seat_snapshots | 4,226 | 4,226 | yes |
| section_rankings (term 202701) | 3,783 | 3,783 | yes |
| section_rankings (all terms) | 3,783 | 3,783 | yes |
| ingest_runs | 112 | 112 | yes |

Result: every count is identical, so the dry run wrote nothing.

## Comparison with research (sanity only)

Figures from 09-RESEARCH.md (2026-09-29) against this run (2026-09-30). None of these are pass conditions. Explanations marked "(hypothesis)" were not verified, because verifying them would need a second USF request, which this plan forbids.

| Metric | Research 2026-09-29 | Dry run 2026-09-30 | Delta | Explanation |
|--------|---------------------|--------------------|-------|-------------|
| Total rows | 6,640 (6,663 on 09-28) | 6,645 | +5 | USF adds and drops sections daily; within normal drift |
| Distinct CRNs | 6,640 | 6,645 | +5 | Same as total rows; still no duplicate CRNs |
| Graduate rows | 2,940 | 2,941 | +1 | Normal drift |
| In-scope rows | 3,700 | 3,704 | +4 | Normal drift |
| Courses in scope | 1,370 | 1,372 | +2 | Two more undergraduate courses appeared |
| Non-Tampa rows | 0 | 0 | 0 | As expected |
| Bytes | 7,098,264 | 7,103,329 | +5,065 | Tracks the +5 rows |
| Fetch time | 15.9 s | 15.2 s | -0.7 s | Normal variation |
| Removals | 104 | 105 | +1 | Normal drift |
| New CRNs (inserts) | 21 total, 10 in already-tracked courses | 12 inserts | +2 vs 10 | The dry run counts only inserts into tracked courses; CRNs of not-yet-tracked courses show up under would-add (consistent with the +2 in-scope courses) |
| Would-add courses | 11 | 13 | +2 | Two more new undergraduate courses since 09-29 (matches the +2 course keys) |
| Instructor changes | 89 | 150 | +61 | Larger than day-to-day drift alone suggests (hypothesis: departments assigning instructors to Staff sections as registration nears, and the research diff counted with a different definition). Worth a look at the first real sweep; not a gate issue |
| Seat changes | 85 | 97 | +12 | Seats move continuously; expected |
| Updated (distinct changed sections) | not reported | 543 | n/a | Exceeds removals + instructor + seat changes taken separately (at most 352 with no overlap), so at least about 190 sections also change other fields (hypothesis: title, dates, status or enrollment columns). The dry-run line has no per-field breakdown |
| Peak RSS | 121 MB (parse only, prototype) | 228 MiB (whole sweep) | n/a | Different scope: this includes imports and DB staging; still well under the 350 MB target |
| Tail error | present | present | none | Confirms Pitfall 1 on live data; gate handled it |

## Earliest Blueprint creation

Dry-run sweep start: 2026-09-30T05:15:45.689Z. Adding the 60-minute floor (D-01 floor, D-22 outside a registration window) gives:

**Earliest Blueprint creation: 2026-09-30T06:15:46Z (UTC)**, which matches the dry run's own `next_start_at` of 2026-09-30T06:15:45.689Z. Creating the Blueprint earlier would let the hosted worker's first sweep fall inside the floor of the last USF request.

## CI and merge

Recorded 2026-09-30T05:37:45Z (UTC). The operator pushed nothing themselves: after the `push-approved` reply and adding the `workflow` token scope, the executor ran `git push -u origin HEAD` and `gh pr create --base main --fill`. The merge was the operator's action.

| Item | Value |
|------|-------|
| PR | #33, https://github.com/aatif101/easy-A/pull/33 |
| State | MERGED at 2026-09-30T05:36:53Z |
| Merge commit | `5def3562824599d5705d286fee3b8dc046facc76` |
| `origin/main` after `git fetch origin` | `5def3562824599d5705d286fee3b8dc046facc76` (equals the merge commit) |
| PR head that was tested | `79f9efd21a00742aa89949c93775b1f28f67a131` |

### First CI run (head b2e89cc): python failed, two test bugs

The first python job failed with 2 failed and 691 passed. Both failures were test-only bugs that appear once the PostgreSQL service is really used (the merge blocker the plan wanted to surface):

1. `tests/refresh/test_postgres_coverage.py`: assumed the seeded MAC 1105 course was `rows[0]`; the regenerated Tampa-wide target list makes `rows[0]` ACG 2021. Fixed by selecting the row by key.
2. `tests/test_database_config.py::test_missing_database_url_fails_loudly`: CI sets `MIGRATION_DATABASE_URL` for Alembic and the test cleared only `DATABASE_URL`. Fixed by also clearing `MIGRATION_DATABASE_URL`.

Fix commit `79f9efd` was pushed to the same branch. The web and docker jobs passed on both heads.

### Final CI on head 79f9efd

| Job | push run | pull_request run |
|-----|----------|------------------|
| python | success | success |
| web | success | success |
| docker | success | success |

- push run: https://github.com/aatif101/easy-A/actions/runs/36673205961
- pull_request run: https://github.com/aatif101/easy-A/actions/runs/36673209773

Python job log checks (both runs):

- Pytest summary present: `693 passed, 1 warning`.
- No pytest skip line for "Set EASY_A_TEST_POSTGRES_URL". The only two textual matches are the workflow's own guard step; that step printed "No PostgreSQL integration test was skipped."
- Alembic round-trip on postgres:16: `upgrade head` (0001 to 0004), `downgrade -1` (0004 to 0003) and `upgrade head` (0003 to 0004) all succeeded.
- Frontend tests: 96 passed.

### Post-merge run on main

A push run on the merge commit (https://github.com/aatif101/easy-A/actions/runs/36674223585) was in progress when this section was written (web and docker success, python still running).

---

# Go-live and first hosted sweep (plan 09-15)

All probes below are read-only: `render services` / `render deploys list` / `render logs`, plain HTTP GETs against the operator's own hosted URLs, and database reads inside `SET TRANSACTION READ ONLY` transactions (each reported `transaction_read_only = on`). No Render service or environment variable was created, changed, deployed or deleted by the executor. No connection string, pooler hostname or credential appears in this file.

## Go-live

Operator reply (Task 1, typed in the main session): `live api=https://easy-a-api.onrender.com web=https://easy-a-web.onrender.com`. Precondition met: the "CI and merge" section above records PR #33 merged as `5def356` with all jobs green, docs PR #34 merged as `b485efb`, and the current time (2026-09-30T18:27Z) is after the earliest Blueprint creation time (2026-09-30T06:15:46Z).

Verified 2026-09-30T18:27:19Z through 18:27:29Z (UTC).

| Check | Result |
|-------|--------|
| Services (`render services --output json`) | 3 services, all `not_suspended`, branch `main`, auto-deploy on |
| `easy-a-api` | `srv-daul6tfpn0mc7384h4fg`, web service, region ohio, plan starter, https://easy-a-api.onrender.com, health check path `/health` |
| `easy-a-worker` | `srv-daul6tnpn0mc7384h5jg`, background worker, region ohio, plan starter |
| `easy-a-web` | `srv-daul6tfpn0mc7384h50g`, static site, https://easy-a-web.onrender.com. A static site has no region setting in `render.yaml` or the CLI output (it is served from Render's CDN), so the "ohio" check applies to the API and worker only |
| Worker deploy | `dep-daul6tvpn0mc7384h6eg`, status `live`, trigger `blueprint_sync`, created 2026-09-30T18:22:47Z, finished 2026-09-30T18:23:25Z, commit `b485efb91e95aae0ec93f5578636a8f1c7542f99` (equals `origin/main` after `git fetch`) |
| `GET <API>/health` | HTTP 200, body `{"status":"ok"}` |
| `GET <WEB>/` | HTTP 200 |
| CORS: `GET <API>/api/v1/metadata/terms` with `Origin: https://easy-a-web.onrender.com` | HTTP 200, `access-control-allow-origin: https://easy-a-web.onrender.com` (exactly the web origin, no trailing slash), `vary: Origin`. PASS |
| API service error-level logs (`render logs -r <api-id> --level error`) | none returned |

Static build check (GET of the built bundle `assets/index-DDdxXJZY.js`, 235,457 bytes): the real API origin `easy-a-api.onrender.com` appears in the bundle and `localhost:8000` does not. The front end code (`web/src/api/rankings.ts`) only uses synthetic data when `VITE_USE_MOCK_DATA === "true"`, so a build that points at the real API is not in mock mode. The literal `VITE_USE_MOCK_DATA` value baked into the build cannot be read back from the bundle and is not claimed beyond that inference. Email notification settings (D-09) live in the dashboard and cannot be read by the CLI; they rest on the operator's confirmation and are NOT independently verified here.

## First hosted sweep

The worker started at 18:23:25Z and ran its first sweep immediately (`worker_started` logged `last_sweep_started_at: null`, because the earlier real-data dry run wrote no IngestRun). `GET <API>/api/v1/metadata/sync-status?term=202701` at 2026-09-30T18:27:29Z:

| Field | Value |
|-------|-------|
| last_success_at | 2026-09-30T18:24:16.387516Z |
| last_run_at | 2026-09-30T18:23:25.697115Z |
| last_status | succeeded |
| last_error_kind | null |
| last_records_failed | 4 (the four courses deferred by the per-sweep add cap, see below) |
| failures_last_24h | 0 |
| in_registration_window | false |
| cadence_seconds / stale_after_seconds | 3600 / 7200 |
| is_stale | false |

No retry was needed (last_success_at was already set).

`sweep_succeeded` line from `render logs -r srv-daul6tnpn0mc7384h5jg --text sweep_succeeded` (logged 2026-09-30 18:24:16 UTC):

| Field | Value |
|-------|-------|
| started_at | 2026-09-30T18:23:25.697115Z |
| duration_s | **50.69** |
| bytes | 7,100,787 |
| content_encoding | null (USF returned an uncompressed body) |
| tail_error | true (the known USF error tail, not a failure) |
| scope | total_rows 6,643; distinct_crns 6,643; non_tampa_rows 0; graduate_rows 2,941; unparseable_number_rows 0; in_scope_rows 3,702; subjects 210; course_keys 1,372 |
| inserted | 24 |
| updated | 560 |
| removed | 109 |
| restored | 0 |
| instructor_changes | 156 |
| seat_changes | 100 |
| auto_added (10) | ARH 4301, ART 3781C, ART 4930, FIL 4839, FIN 4934, FRE 2201, HUM 4368, HUM 4391, HUM 4434, HUM 4890 |
| unapplied courses (4, by name) | LDR 3363, LDR 4204, NEB 0001, POT 4936 (each "deferred: per-sweep cap") |
| would_add | empty |
| gate_reasons | empty |
| error_kind / error_detail | null / null |
| peak_rss_mb | 193.6 |
| next_start_at (in the sweep line) | 2026-09-30T19:23:25.697115Z |

Following `sleeping` line (18:24:16 UTC): `next_start_at` = **2026-09-30T19:32:01.016767Z**, which is 68 minutes 36 seconds after the sweep start, later than the 60-minute floor (the jitter on top of the floor). Sweep 2 is therefore expected no earlier than 19:32:01Z.

Observations recorded without interpretation beyond what is stated:

- **Sweep duration FAIL against the 30 s soak criterion for this sweep.** The first sweep took 50.69 s end to end, against "each sweep takes under 30 s". This sweep applied the whole catch-up (24 inserts, 560 updates, 109 removals, 156 instructor and 100 seat changes, 10 auto-added courses plus cache refresh), so it is the heaviest sweep the worker will do; the dry run that only read and diffed took 15.2 s. Whether steady-state sweeps stay under 30 s is decided by the later sweeps in the soak. The threshold was not changed.
- **Memory:** `peak_rss_mb` 193.6 from the sweep's own log line, under the 350 MB target and the 512 MB plan limit (Render Metrics not yet read; that is an operator step in Task 3).
- **Per-sweep add cap:** 10 courses were auto-added and 4 were deferred to a later sweep, which is why `last_records_failed` is 4 and the IngestRun `error_message` lists the four unapplied courses. The next sweep(s) should add them; their new sections will then count as inserts in that sweep.
- **Drift against the dry run (12 hours earlier):** total rows 6,643 (dry run 6,645), removals 109 (105), instructor changes 156 (150), seat changes 100 (97), inserts 24 (12 plus would-add), FRE 2201 newly appeared as an auto-added course. USF changes daily; none of this is a gate issue.

### Database snapshot 1 (READ ONLY, 2026-09-30T18:29:39Z)

This is soak snapshot 1 (taken after sweep 1 and before sweep 2). The pre-deploy counts come from "Row counts before/after" above.

| Item | Pre-deploy (05:16Z) | Snapshot 1 | Delta | Reconciliation with the sweep line |
|------|---------------------|------------|-------|-------------------------------------|
| sections (all) | 3,783 | 3,807 | +24 | equals inserted (24) |
| active 202701 sections (`removed_at IS NULL`) | 3,783 | 3,698 | -85 | 3,783 + 24 inserted - 109 removed = 3,698 |
| removed 202701 sections | 0 | 109 | +109 | equals removed (109) |
| section_instructors | 4,226 | 4,406 | +180 | 156 instructor_changes + 24 inserted = 180 |
| seat_snapshots | 4,226 | 4,350 | +124 | 100 seat_changes + 24 inserted = 124 |
| section_rankings (202701) | 3,783 | 3,698 | -85 | equals the active count |
| ingest_runs | 112 | 113 | +1 | one sweep |

Latest IngestRun for `usf_schedule_sync:202701`: id 113, status `succeeded`, started 2026-09-30 18:23:25.697115+00, finished 18:24:16.387516+00, records_seen 3,702, records_inserted 24, records_updated 560, records_failed 4, error_message lists the four deferred courses.

Auto-added courses (courses with active 202701 sections that are not configured targets): exactly the 10 named in the sweep line, all catalog edition 2026-2027. Their `section_rankings.score_source` values: `subject` for all 11 sections across the 10 courses (HUM 4391 has 2 sections, the rest 1), and none is `course`. No auto-added course shows own-course history, as required (PROJECT.md D-20). Overall 202701 score_source split: course 3,330; subject 319; global 49 (total 3,698). Rankings rows belonging to removed sections: 0. Active sections without a ranking row: 0.

## Hosted search and p95

### Search total equals the active count

Checked 2026-09-30T18:30:15Z. `GET <API>/api/v1/rankings/search?term=202701&limit=50` (probe at 18:29:51Z) returned `total: 3698`. The executor then paged through the whole result with `limit=200` (19 GETs) and compared against a READ ONLY database read:

| Check | Result |
|-------|--------|
| API total | 3,698 |
| CRNs collected across all pages / distinct | 3,698 / 3,698 |
| DB active 202701 sections | 3,698 |
| API CRN set equals the DB active CRN set | yes (0 in API only, 0 in DB only) |
| Removed CRNs (109) present in the API results | 0 |

Result: PASS. The earlier spot-check of three removed CRNs (10525, 10832, 11141) with a `q=` parameter was not a valid probe (the endpoint has no free-text `q` parameter, so the total stayed 3,698); the full set comparison above replaces it.

### Hosted p95

Command: `uv run python scripts/benchmark_rankings_search.py --remote-url https://easy-a-api.onrender.com --iterations 50` (5 warmups, run once). Run 2026-09-30T18:30:32Z from the operator's workstation.

| Measure | Value |
|---------|-------|
| Mode | remote HTTPS request + body + JSON validation (no DB reconciliation) |
| Dataset size | 3,698 sections (hosted API total) |
| p50 | 131.53 ms |
| p95 | **212.56 ms** |
| max | 371.92 ms |
| Against the 1,500 ms bar | PASS (14.2 percent of the bar) |

This is deployed-host, single-client latency over the public internet from one workstation. **Browser latency and concurrent-user latency: NOT MEASURED** (D-08; REQ-PERF-01 re-check covers single-client hosted p95 only).

## D-21 re-baseline after sync

Read-only probes run 2026-09-30T18:30:47Z (validator) and 18:33:00Z (inventory) against hosted Supabase. `08-D21-EXCEPTIONS.md` was not regenerated (`--exceptions-md` was not passed); it remains the dated 2026-09-24 record.

`uv run python scripts/validate_tampa_ingest.py --term 202701 --targets config/course_targets.toml` (exit 0):

```
PASS suffix-exact
INFO auto-added (D-05): 10 course(s): ARH 4301, ART 3781C, ART 4930, FIL 4839, FIN 4934, FRE 2201, HUM 4368, HUM 4391, HUM 4434, HUM 4890
PASS reconciliation
PASS honest-coverage (verified non-letter-grade exceptions: 284)
```

`uv run python scripts/inventory_tampa_grades.py --term 202701` (exit 0), verdicts `integrity: PASS`, `d21_grade_coverage: PASS`:

| Item | 2026-09-24 record (08-D21-EXCEPTIONS.md / STATE.md) | After the first sync (2026-09-30) |
|------|------------------------------------------------------|------------------------------------|
| Active sections inventoried | 3,783 | 3,698 |
| Courses represented | not recorded in this file | 1,368 |
| Evidence-backed sections | 3,122 | 3,046 |
| Listed exceptions (sections) | 661 | 652 |
| no_rows | 361 | 368 |
| non_letter_grade | 300 | 284 |
| Evidence-backed courses | 1,117 (STATE.md) | 1,081 |
| Exception courses (no_rows, non_letter_grade) | not recorded in this file | 238, 49 |
| Grade rows stored | not recorded in this file | 8,662 (latest grade ingest 2026-09-23T21:36:34Z, unchanged) |
| Integrity: unattributed grade rows, bucket-sum mismatches, rows at/after the term, stale cache, non-Tampa sections | PASS | 0, 0, 0, false, 0 (PASS) |

Arithmetic: 3,046 + 368 + 284 = 3,698. The shift is explained by the sync (109 removals, 24 inserts, 10 new courses whose sections fall back to subject-level data) and is not a change to the grade data, which was not touched. The validator's verified non-letter-grade exception count (284) equals the inventory's `non_letter_grade` section count (284).

## Soak

Recorded 2026-09-30, probes between 20:04Z and 20:08Z (UTC). Everything the executor ran was read-only: `render logs` / `render deploys list`, public GETs to `https://easy-a-api.onrender.com`, and database reads inside `SET TRANSACTION READ ONLY` transactions (each reported `transaction_read_only = on`). No sweep, restart, deploy or Render setting was triggered by the executor. No connection string, pooler hostname or credential appears here. Items taken from the operator are labelled "operator-reported" and were not independently verified unless stated.

### Sweeps covered

Two sweeps succeeded. Sweep 3 was due at 2026-09-30T20:38:57Z and had **not** run when snapshot 2 was taken (20:05:25Z; worker logs held no `sweep_succeeded` line after 19:32:38Z). Snapshot 2 therefore covers exactly sweep 2 after snapshot 1; it does not cover sweep 3. No "later sweep" data beyond sweep 2 is claimed.

| Sweep | IngestRun id | started_at (UTC) | finished_at (UTC) | status |
|-------|--------------|------------------|-------------------|--------|
| 1 | 113 | 2026-09-30 18:23:25.697115 | 18:24:16.387516 | succeeded |
| 2 | 114 | 2026-09-30 19:32:01.016933 | 19:32:38.183183 | succeeded |

Sweep 2 started 68 min 35 s (4,115.3 s) after sweep 1 started, outside a registration window (`in_registration_window: false`), so the "at least 60 minutes after the first" condition holds.

### Sweep 2 line (`sweep_succeeded`, logged 19:32:38Z)

Copied from the worker's log (operator pasted it; the orchestrator and this run re-read it from `render logs` and it matches):

| Field | Value |
|-------|-------|
| duration_s | **37.166** |
| bytes / content_encoding | 7,099,014 / null (uncompressed) |
| tail_error | true (the known USF error tail, not a failure) |
| scope | total_rows 6,641; in_scope_rows 3,704; subjects 210; course_keys 1,372; non_tampa_rows 0; graduate_rows 2,937 |
| inserted / updated / removed / restored | 5 / 49 / 0 / 0 |
| instructor_changes / seat_changes | 6 / 1 |
| auto_added (3) | LDR 3363, LDR 4204, POT 4936 (the three deferred by sweep 1's per-sweep cap) |
| unapplied_courses | NEB 0001 (no catalog heading) |
| gate_reasons / error_kind | empty / null |
| peak_rss_mb | 223.4 |
| next_start_at (in the sweep line) | 2026-09-30T20:32:01.016933Z |

### Database snapshot 2 (READ ONLY, 2026-09-30T20:05:25Z) reconciled against sweep 2

| Item | Snapshot 1 (18:29:39Z) | Snapshot 2 (20:05:25Z) | Delta | Expected from the sweep 2 line | Match |
|------|------------------------|------------------------|-------|--------------------------------|-------|
| section_instructors | 4,406 | 4,417 | +11 | instructor_changes 6 + inserted 5 = 11 | yes |
| seat_snapshots | 4,350 | 4,356 | +6 | seat_changes 1 + inserted 5 = 6 | yes |
| sections (all) | 3,807 | 3,812 | +5 | inserted 5 | yes |
| active 202701 sections | 3,698 | 3,703 | +5 | inserted 5, removed 0, restored 0 | yes |
| removed 202701 sections | 109 | 109 | 0 | removed 0, restored 0 | yes |
| section_rankings (202701) | 3,698 | 3,703 | +5 | equals the active count | yes |
| ingest_runs | 113 | 114 | +1 | one sweep | yes |

Result: **PASS, exact equality on every row.** `49 updated` sections added no instructor or seat rows beyond the 6 and 1 logged changes: the 11 new `section_instructors` rows all carry the same `observed_at` (19:32:22.591363Z, sweep 2's write time) and split into 5 first-ever rows (new sections) plus 6 name changes; unchanged sections wrote nothing. Change-only writes are demonstrated on the hosted system for this sweep (ROADMAP criterion 4: "an unchanged sweep writes no instructor or seat rows").

Row growth (Open Question 6, seat_snapshots after the initial sync): 4,226 (pre-deploy) to 4,350 (sweep 1, +124, includes the catch-up) to 4,356 (sweep 2, +6). The steady-state rate at this point is 6 rows per sweep; this covers one non-catch-up sweep only and is not a projection. Growth during registration windows (5-minute cadence) is NOT MEASURED.

Score-source split after sweep 2 (202701): course 3,332; subject 322; global 49 (total 3,703). Versus snapshot 1 the 5 inserted sections are 3 `subject` (the three newly auto-added courses, 1 section each) and 2 `course` (new sections in already-tracked courses). The 13 courses with active sections that are not configured targets (the 10 from sweep 1 plus LDR 3363, LDR 4204, POT 4936) have `score_source` `subject` on every section (HUM 4391 has 2, the others 1; 14 sections in all), none `course`, so no auto-added course shows own-course history (PROJECT.md D-20). Rankings rows belonging to removed sections: 0. Active sections without a ranking row: 0.

The difference between the sweep's `in_scope_rows` and the active count is explained by the one unapplied course: sweep 1 3,702 in scope vs 3,698 active (4 deferred courses, each 1 section: LDR 3363, LDR 4204, POT 4936, NEB 0001) and sweep 2 3,704 in scope vs 3,703 active (NEB 0001 still unapplied). The "1 section per deferred course" part is inferred from the four-to-zero-to-one arithmetic, not read from the course pages.

### failures_last_24h and freshness

`GET <API>/api/v1/metadata/sync-status?term=202701` at 2026-09-30T20:05:19Z:

| Field | Value |
|-------|-------|
| last_success_at | 2026-09-30T19:32:38.183183Z |
| last_run_at | 2026-09-30T19:32:01.016933Z |
| last_status | succeeded |
| last_error_kind | null |
| last_records_failed | 1 (NEB 0001, see below) |
| **failures_last_24h** | **0** |
| in_registration_window | false |
| cadence_seconds / stale_after_seconds | 3600 / 7200 |
| is_stale | false |

The orchestrator's earlier read (19:51:48Z) agreed: succeeded, failures_last_24h 0, is_stale false, last_records_failed 1.

### Soak criteria scorecard

| Criterion (09-15 must_haves) | Result | Basis |
|------------------------------|--------|-------|
| At least two sweeps succeeded, at least 60 min apart, outside a window | PASS | IngestRuns 113 and 114; 68.6 min apart |
| Change-only: new instructor and seat rows equal the logged changes | PASS | table above, exact |
| Removed sections stay out of search | PASS | re-run at 2026-09-30T20:08:36Z: the API's paged search result (19 GETs, `limit=200`) has total 3,703, 3,703 distinct CRNs, equals the DB active CRN set exactly (0 in API only, 0 in DB only), and contains 0 of the 109 removed CRNs; 0 rankings rows belong to removed sections |
| Each sweep under 30 s end to end | **GAP (not met)** | 50.69 s and 37.166 s, see next section |
| Worker under 512 MB, target under 350 MB, no OOM restarts | PASS on the evidence available | the sweeps' own `peak_rss_mb` 193.6 and 223.4; operator-reported Render Metrics peak "under 350 MB" (no exact number given; not independently read, the CLI cannot show Metrics). `render logs --level error` for the worker returned zero lines from 18:23Z to 20:08Z, the worker's event sequence (worker_started, sweep_succeeded, sleeping, sweep_succeeded, sleeping, then the operator's restart) shows no unexplained restart, and `render deploys list` shows one deploy, so no deploy-triggered restart either. Render's own OOM event list is a dashboard view and was not read by the executor. The only restart was the operator's single one below |
| Restart logs `worker_stopped`; new instance does not sweep immediately | PASS | see "Restart check" |
| Students see "Updated N min ago", no stale warning | operator approved; no itemized results reported | executor did not open the web UI. The API data behind it is consistent: is_stale false, last_success_at 33 min before the probe |
| A Staff-to-named instructor change appears on the hosted site | PASS at the API level; UI not independently viewed | see "Instructor-change spot check" |

### Sweep duration: GAP against the 30 s criterion (unresolved)

| Sweep | duration_s | Against "each sweep under 30 s" |
|-------|-----------|----------------------------------|
| 1 (full catch-up) | 50.69 | over by 20.69 s |
| 2 (5 inserts, 49 updates, 0 removals) | 37.166 | over by 7.166 s |
| Dry run from the workstation (reads and diffs only, 09-14) | 15.209 | not comparable (different host, nothing written) |

Both hosted sweeps exceed the criterion. **This is recorded as a gap, not a pass, and the 30 s threshold was not loosened.** The operator has not decided whether to accept it. Sweep 2 was a light sweep (5 inserts, 49 updates, 6 instructor changes, 1 seat change, no removals), so write volume alone does not explain the overage. The log line gives no per-phase breakdown, so the cause is not established. Hypotheses, none tested: the 0.5 CPU Starter worker parses the 7.1 MB body more slowly than a workstation; the fetch from Render is slower than from the workstation; the per-sweep database work over the pooler adds round trips. Sweep 3 (due about 20:38:57Z) is a third data point. The 30 s figure came from the RESEARCH pitfall and the live-sync plan soak criteria, not from a user-facing requirement; whether it is the right bar is for the operator to decide (see the SUMMARY user-review list).

### Restart check (assumption A1 and the restart floor)

The operator restarted `easy-a-worker` once with `render restart srv-daul6tnpn0mc7384h5jg` at about 20:00:5xZ (operator-reported time; between sweeps 2 and 3). The worker logs (re-read with `render logs` for this section) show:

| Time (UTC) | Event |
|------------|-------|
| 19:32:38 | sweep 2 `sweep_succeeded`, then `sleeping` with next_start_at 2026-09-30T20:37:58.874589Z |
| 20:00:58 | new instance `worker_started`, `last_sweep_started_at` 2026-09-30T19:32:01.016933Z |
| 20:00:58 | new instance `sleeping`, next_start_at 2026-09-30T20:38:57.484266Z |
| 20:01:57.008 | `{"event": "worker_stopped"}` from the old instance (operator confirmed it was the old instance) |

- **A1 confirmed:** SIGTERM reached the Python process of the old instance, which logged `worker_stopped` (20:01:57, about 59 s after the new instance started, consistent with Render's deploy/restart overlap).
- **Restart floor held (D-01, PROJECT.md D-22(b)):** the new instance did not sweep. Its next_start_at of 20:38:57Z is 66 min 57 s after the last sweep start and later than the 20:32:01Z floor (last sweep start plus 60 min). No sweep line appears between 19:32:38 and the probe.
- One restart only (no repeated restarts; the REQ-SYNC-01 prohibition held).

### Jitter observation

The operator's working note was that sweep 1's next start was +68.6 min but sweep 2's was exactly +60 min. The logs show that comparison mixes two different fields:

| Sweep | `next_start_at` field inside the `sweep_succeeded` line | `next_start_at` of the following `sleeping` line |
|-------|-----------------------------------------------------------|---------------------------------------------------|
| 1 (start 18:23:25.697) | 19:23:25.697 (+60.00 min) | 19:32:01.017 (+68.59 min) |
| 2 (start 19:32:01.017) | 20:32:01.017 (+60.00 min) | 20:37:58.875 (+65.96 min) |
| after restart (last start 19:32:01.017) | n/a | 20:38:57.484 (+66.94 min) |

The field in the sweep line is the floor (start plus exactly 60 min) in both sweeps. The sleep target, which is what the worker actually waits for, carries jitter every time (+8.59, +5.96 and, after the restart, +6.94 min beyond the floor). Sweep 2 actually started at 19:32:01.016933, 166 microseconds after the logged sleep target for sweep 1. Observation only: the real gap between sweeps is 66 to 69 min, longer than the nominal 60 min cadence by the jitter, still under `stale_after_seconds` 7200.

### Instructor-change spot check (read-only)

Sweep 2's 6 instructor changes, from `section_instructors` rows observed at 19:32:22.591363Z (snapshot query, database read), compared against the hosted API (`/api/v1/rankings/search?term=202701`, paged, `instructor` field, `instructor_provenance.freshness: current`):

| CRN | Course | Change | Hosted API instructor |
|-----|--------|--------|------------------------|
| 13492 | RED 4943 | Staff to J. King | J. King |
| 16962 | RED 4312 | Staff to S. Esman | S. Esman |
| 18182 | RED 4943 | Staff to L. Kelly | L. Kelly |
| 13490 | RED 4943 | L. Kelly to J. King | J. King |
| 20324 | RED 4312 | J. Outlaw to S. Esman | S. Esman |
| 20773 | INR 2002 | E. Fruehauf to Y. Hermida | Y. Hermida |

The other 5 new rows are first-ever instructors for the 5 newly inserted sections (CRNs 11313, 19200, 20726, 20774, 20775). The hosted API serves the new names for all six changed sections, including three Staff-to-named changes. This was checked against the API and database only. It was not checked against the USF schedule page (that would be an extra USF request, outside D-22) and not through the web UI. Note the sweep applies what the whole-term request returned, so USF is the source of these names by construction.

### Operator approval and what was not itemized

The operator replied "approved" and said peak memory was under 350 MB (operator-observed in Render Metrics, no exact number). The operator did NOT itemize the web-UI checks (the "Updated N min ago" line, the absence of the stale warning, search results, removed CRN not listed) or the instructor-change spot check. They are recorded as **operator approved; no itemized results reported**. The executor's own verification is limited to the API, log and database probes above.

### NEB 0001 (permanent failed record)

NEB 0001 has appeared as unapplied in both sweeps: "deferred: per-sweep cap" in sweep 1, then "no catalog heading" in sweep 2 when the cap no longer applied. The sweep status is still `succeeded` with `records_failed` 1, and `failures_last_24h` counts 0, so it does not raise the failure signal. Expectation (hypothesis, only two sweeps observed): every later sweep will keep reporting one failed record for this course, because the catalog has no heading for it, unless a negative cache suppresses the retry. Students cannot find NEB 0001 sections (they are not inserted). This is for the operator to decide whether to accept, exclude the course, or fix.

### Instructor-change delta: sweep 1 breakdown (150 in the dry run and 156 in sweep 1 versus 89 in research)

READ ONLY query at about 20:10Z over the `section_instructors` rows written by sweep 1 (all 180 rows share `observed_at` 2026-09-30 18:23:46.124294Z), classified by comparing each row with the section's previous row:

| Class | Sweep 1 (2026-09-30) | Research diff (2026-09-29) |
|-------|----------------------|----------------------------|
| Staff to named | 112 | 52 |
| named to other named | 30 | 24 |
| named to Staff | 14 | 13 |
| Total instructor changes | 156 (equals the sweep line) | 89 |
| First-ever rows (new sections) | 24 (equals `inserted`) | n/a |

Both diffs compare USF against the same stored 2026-09-22 data, so the extra 67 changes are a day of USF drift plus any definitional difference between the two diffs. Nearly all the growth is in Staff to named (+60); the other two classes moved by +6 and +1. Hypothesis, not tested: departments assigned instructors to Staff sections as registration nears (this matches the dry-run note), or the research diff counted differently. The cause stays unverified; the hosted database matches what USF returned, so this is an open observation and not a correctness failure.

## Sweep 3 (read-only, from the 09-16 re-verification)

IngestRun 115 started 2026-09-30T20:38:57Z, exactly at the recorded `next_start_at` after the operator's restart, and succeeded in 27.209 s (under the 30 s bar that the operator had accepted as unmet for sweeps 1 and 2). 0 inserted, 10 updated, 1 failed record (NEB 0001, no catalog heading). It wrote 2 instructor rows and 1 seat row, which supports change-only writes.

## Post-merge deploy of the CR-01 fix (PR #35)

- PR #35 merged to main as `046aa5d` (2026-09-30). CI on that commit: success.
- Render redeployed `easy-a-worker` and `easy-a-api` on `046aa5d` (both deploys reported live at about 2026-09-30T23:25Z). The static web site was not rebuilt (its build filter does not include the changed paths).
- Worker after the redeploy: `worker_started` with `last_sweep_started_at` 2026-09-30T22:54:23Z, then `sleeping` until `next_start_at` 2026-09-30T23:58:46Z, which is after the 60-minute floor from the last sweep. No early sweep.
- `/health` ok, web 200, `/api/v1/metadata/sync-status?term=202701` reported `last_status` succeeded, `failures_last_24h` 0, `is_stale` false at 2026-09-30T23:24Z.
- The gate-recovery playbook on main now matches the deployed code. A rehearsal of the recovery on the deployed image has not been done.
