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
