# Phase 8: MVP1-P5 End-to-end MVP-1 verification — Research

**Researched:** 2026-09-23
**Domain:** Live data and product contract verification
**Confidence:** HIGH for repository behavior and dated evidence; MEDIUM for live-state continuity until rerun

> **Superseded in part (2026-09-23, after the grade import and PROJECT.md D-21).** This research
> was written before the grade import. Its grade-coverage figures (132 of 3,783 sections, 563
> subject, 3,088 global) and the recommendation to route a grade-source/import follow-up are
> superseded. Live read on 2026-09-23: 3,122 evidence-backed sections; 661 listed D-21 exceptions
> (311 subject, 50 global, 300 `course` with `effective_n = 0`). The MVP-1 grade criterion is now
> D-21 (evidence-backed or listed source-limited exception; fallbacks never count as course
> history), and Phase 8 does no grade sourcing. Note also that `assert_honest_coverage` in
> `scripts/validate_tampa_ingest.py` rejects the 300 `course`/`effective_n = 0` rows as written;
> plan 08-02 encodes the D-21 non-letter-grade exception there. Everything else below is reusable.

## User Constraints

No Phase 8 `CONTEXT.md` exists. The controlling constraints are the milestone and D-01–D-20 decisions in `PROJECT.md`, the live facts in `STATE.md`, and the Phase 8 success criteria in `ROADMAP.md`. [VERIFIED: .planning/PROJECT.md:23-32,302-329; .planning/STATE.md:16-69; .planning/ROADMAP.md:434-446]

## Project Constraints (from AGENTS.md)

- Preserve the existing stack and frozen historical scoring algorithm; seats, modality, GenEd and syllabus signals do not enter scoring. [VERIFIED: AGENTS.md:15-44]
- Never represent `effective_n = 0` global prior as course history; preserve explicit unavailable states and provenance. [VERIFIED: AGENTS.md:32-50]
- Preserve term/CRN/source identity and deduplication; never commit raw grade exports. [VERIFIED: AGENTS.md:43-51]
- No fabricated coverage, scraping, broad USF crawling, AI features, auth/accounts, or auto-registration. [VERIFIED: AGENTS.md:40-55]
- Fetch and verify `origin/main` before branch or worktree operations; preserve unrelated untracked work. [VERIFIED: AGENTS.md:51-56]
- `.planning/STATE.md` owns volatile counts and next action; older counts in planning artifacts are dated history. [VERIFIED: AGENTS.md:8-28]
- Earlier `docs/` handoff proposals are not accepted scope. [VERIFIED: AGENTS.md:68-75]

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| REQ-COVERAGE-03 | All roughly 3,782 Tampa Spring 2027 sections ingested and searchable; target, stored and API counts reconcile. [VERIFIED: .planning/REQUIREMENTS.md:178-184] | Existing read-only scale validator and HTTP total/page checks. [VERIFIED: scripts/validate_tampa_ingest.py:108-238; scripts/benchmark_rankings_search.py:243-310] |
| REQ-GRADES-01 | Imported historical distributions produce real course analytics; source totals reconcile; lacking courses are explicitly recorded. [VERIFIED: .planning/REQUIREMENTS.md:186-210] | Per-course source ledger, live grade/cache inventory, D-20 assertions, and UI truthfulness checks. [VERIFIED: .planning/phases/05-mvp1-p2-grade-data-sourcing-import-to-supabase/05-IMPORT-RECORD.md:1-33; scripts/validate_tampa_ingest.py:157-190] |
| REQ-PERF-01 | Hosted Supabase search p95 below approximately 1.5 seconds at full scale with scoring/API unchanged. [VERIFIED: .planning/REQUIREMENTS.md:213-224] | Existing 50-call loopback HTTP harness and Phase 7 report. [VERIFIED: scripts/benchmark_rankings_search.py:85-151,243-310; .planning/phases/07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s/07-PERF-REPORT.md:133-178] |
</phase_requirements>

## Summary

Phase 8 should independently rerun the three gates against the same hosted term and record a dated, reproducible evidence report. The existing validators already test suffix identity, count reconciliation, honest fallback states, data quality, and loopback HTTP performance. The Phase 7 measured HTTP p95 was 309.91 ms for 3,783 stored sections; this is dated evidence, not a substitute for a fresh Phase 8 run. [VERIFIED: scripts/validate_tampa_ingest.py:108-238; scripts/benchmark_rankings_search.py:243-310; .planning/phases/07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s/07-PERF-REPORT.md:133-178]

The full MVP-1 milestone remains unmet on current evidence. Its definition says *each* section has imported course history and a score computed from it. The latest state reports 132 of 3,783 sections across 10 of 1,401 represented courses with `score_source=course`; 563 sections use subject fallback and 3,088 use global fallback. Phase 8's softer “grade-derived wherever data exists” criterion can verify honest behavior but cannot itself close that milestone gap. These numbers must be refreshed before final reporting. [VERIFIED: .planning/PROJECT.md:23-27; .planning/STATE.md:32-42; .planning/ROADMAP.md:434-446]

**Primary recommendation:** Produce a read-only, full-term verification report with separate PASS/FAIL/NOT MEASURED verdicts for section coverage, sourced course-grade coverage, quality, API/UI honesty, and p95. If the grade gap persists, report MVP 1 as incomplete and route a bounded grade-source/import follow-up; do not mark the milestone achieved. [VERIFIED: .planning/PROJECT.md:23-27,302-323; .planning/STATE.md:32-42]

## Architectural Responsibility Map

| Capability | Primary tier | Secondary tier | Rationale |
|---|---|---|---|
| Term/CRN, campus and course coverage truth | Database/storage | API/backend | Stored rows are the source; validator and API expose them. [VERIFIED: scripts/validate_tampa_ingest.py:108-155] |
| Source-grade attribution and raw aggregate reconciliation | Database/storage | API/backend | `GradeDistribution` persists source, hash, term, CRN and `course_id`; analytics consume it. [VERIFIED: src/easy_a/models/core.py:87-132; .planning/phases/05-mvp1-p2-grade-data-sourcing-import-to-supabase/05-IMPORT-RECORD.md:1-33] |
| Search latency | API/backend | Database/storage | HTTP harness measures API over hosted database; SQL/cache feed route. [VERIFIED: scripts/benchmark_rankings_search.py:243-310] |
| Student-visible fallback wording | Browser/client | API/backend | UI must render the API's source and denominator honestly. [VERIFIED: web/src/components/RankingTable.tsx:1-97; web/src/components/RankingDetails.tsx:12-90] |
| Final verification verdict | Planning evidence | All tiers | Report must distinguish code behavior, hosted state and unmeasured claims. [VERIFIED: .planning/PROJECT.md:23-27,309-323] |

## Standard Stack

Use the installed repository stack and existing scripts. No new package is justified for this verification phase. Project declarations are Python `>=3.12`, pytest `>=8.3.0`, FastAPI `>=0.141.1`, SQLAlchemy `>=2.0.0`, HTTPX `>=0.28.0`, and the existing React/Vitest frontend; these are declared lower bounds, not claims of exact installed versions. [VERIFIED: pyproject.toml:1-46; web/package.json:1-35]

| Component | Purpose | Use |
|---|---|---|
| `scripts/validate_tampa_ingest.py` | Suffix, count and honest-fallback assertions | Run unchanged against `202701`. [VERIFIED: scripts/validate_tampa_ingest.py:157-238] |
| `scripts/check_data_quality.py` | Full-term error/warning/info report | Capture JSON or concise parsed counts without publishing row-level sensitive material. [VERIFIED: scripts/check_data_quality.py:1-7; src/easy_a/quality/cli.py:16-70] |
| `scripts/benchmark_rankings_search.py` | 50-call live HTTP p95 with 5 warmups | Start local API against the same hosted database and run `--live --http-base-url`. [VERIFIED: scripts/benchmark_rankings_search.py:85-151,243-310] |
| `pytest`, Vitest, ruff, mypy, TypeScript build | Regression gates | Run the relevant suites; record PostgreSQL skips accurately. [VERIFIED: pyproject.toml:24-54; web/package.json:6-12; .planning/STATE.md:52-55] |

**Package legitimacy audit:** Not applicable; no external package installation is recommended.

## Architecture Patterns

### System Architecture Diagram

```text
Existing sourced SGDIS aggregates ──> hosted grade_distributions ──> cached rankings
                                                   │                       │
202701 Tampa schedule ──> hosted sections ──────────┼───────────┐           │
                                                     ▼           ▼           ▼
                              read-only grade inventory   scale validator   rankings API
                                      │                         │                │
                                      └──────────┬──────────────┘                ▼
                                                 ▼                         browser presentation
                              dated evidence + gate verdict <── quality + HTTP p95
                                                 │
                                gap? ──yes──> unmet MVP report + source/import follow-up
                                        no──> milestone acceptance evidence
```

### Pattern 1: Freeze one live snapshot for the report

Record UTC time, branch/commit, target term, database class (hosted Supabase pooler), section/cache/course/subject/grade counts, score-source split, and every command/result. Run the coverage, grade, quality and performance gates close together; if a refresh occurs between them, restart or explicitly label the differing snapshots. This is a recommendation derived from the separate dated Phase 6/7 reports and the current mutable database. [VERIFIED: .planning/phases/07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s/07-PERF-REPORT.md:1-33,133-178; .planning/STATE.md:26-55]

### Pattern 2: Inventory evidence by represented course

Join the distinct `202701` course set to attributed historical `GradeDistribution.course_id` and to `SectionRankingCache` by exact subject/number or section ID. Report each represented course and its section count, historical row count, historical terms/source identifiers, raw grade total, source state, effective-N range and remediation status. Keep a derived aggregate ledger, never workbook rows or connection strings. The model's unique key is verbatim `("term_id", "crn", "source")`; its provenance fields are verbatim `"source"`, `"source_hash"`, `"ingested_at"`. [VERIFIED: src/easy_a/models/core.py:87-132]

### Pattern 3: Gate distinct meanings separately

- **Course history:** verbatim score-source values `"instructor_course"` or `"course"`, with `effective_n > 0`; verify a matching attributed source aggregate, not just a positive score. [VERIFIED: src/easy_a/analytics/confidence.py:18-22; scripts/validate_tampa_ingest.py:157-190]
- **Subject fallback:** verbatim `"subject"`; it is history of other courses in the subject, not this course's distribution. [VERIFIED: src/easy_a/analytics/confidence.py:18-22; .planning/STATE.md:35-42]
- **Global fallback:** verbatim `"global"` and `effective_n = 0`; count it as lacking evidence, even though a numeric score is present. [VERIFIED: src/easy_a/analytics/confidence.py:18-22; scripts/validate_tampa_ingest.py:157-190]

### Recommended project structure

Put any new read-only verification CLI beside `scripts/validate_tampa_ingest.py`, focused tests under `tests/refresh/` or `tests/rankings/`, browser regression tests beside their components, and the dated verification record under this Phase 8 directory. This follows existing paths rather than introducing a new subsystem. [VERIFIED: scripts/validate_tampa_ingest.py:1-25; tests/refresh/test_validate_tampa_ingest.py:1-20; web/src/components/SeatBadge.test.tsx:1-20]

## Don't Hand-Roll

| Problem | Use existing capability | Why |
|---|---|---|
| Full-term count/suffix checks | `validate_tampa_ingest.py` | Already checks cache count, target reconciliation and suffix ownership. [VERIFIED: scripts/validate_tampa_ingest.py:26-155] |
| Percentile benchmark | `benchmark_rankings_search.py --live --http-base-url` | Includes full HTTP body/JSON validation, 5 warmups and 50 measured calls. [VERIFIED: scripts/benchmark_rankings_search.py:134-151,217-239,243-310] |
| Grade file parsing/identity | Existing `ingest_grades.py` pipeline | Existing model uniquely keys term/CRN/source; importing is follow-up scope if sources are available. [VERIFIED: scripts/ingest_grades.py:1-35; src/easy_a/models/core.py:87-132] |
| Numeric-score proof of real history | Explicit source and denominator inventory | A global prior can still yield a numeric score with `effective_n=0`. [VERIFIED: .planning/PROJECT.md:320-323; .planning/STATE.md:35-42] |

## Common Pitfalls

1. **Declaring MVP 1 complete after only the Phase 8 success criteria pass.** `PROJECT.md` says every section has imported historical grades; current state says only 132 do. Keep a separate full-milestone verdict. [VERIFIED: .planning/PROJECT.md:23-27; .planning/STATE.md:35-42; .planning/ROADMAP.md:440-446]
2. **Treating quality 0 errors as full grade coverage.** Phase 7 recorded 0 errors alongside 3,088 `no_historical_analytics` info and 3,088 `low_confidence_ranking` warnings. Report all severity counts and grade gaps. [VERIFIED: .planning/phases/07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s/07-PERF-REPORT.md:111-122]
3. **Calling subject fallback course history.** The same-subject data does not prove that course's outcome distribution. Preserve a three-way course/subject/global inventory. [VERIFIED: .planning/STATE.md:35-42; src/easy_a/analytics/confidence.py:18-22]
4. **Relying only on database/cache totals for API searchability.** `validate_tampa_ingest.py` compares the ranking-cache count, while the HTTP benchmark checks the broad API total. Add deterministic pagination/identity coverage (all pages, no duplicate/missing term+CRN) if claiming every section is searchable. [VERIFIED: scripts/validate_tampa_ingest.py:108-155; scripts/benchmark_rankings_search.py:269-272]
5. **Overstating what performance measured.** The 309.91 ms p95 was loopback HTTP over hosted Supabase; deployed/browser latency has not been measured. [VERIFIED: .planning/phases/07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s/07-PERF-REPORT.md:133-178]
6. **Student-facing fallback wording.** `RankingTable` displays a numeric score and says `"Based on limited historical data."` for low confidence; `RankingDetails` says `"Scores are historical estimates, not guarantees."` even when global `effective_n=0`. It labels source only in expanded details. Test global and subject examples on desktop/mobile, and plan narrowly scoped wording/presentation repair if that wording misleads about evidence. [VERIFIED: web/src/components/RankingTable.tsx:10-11,57-97; web/src/components/RankingDetails.tsx:32-36,89; web/src/utils/rankings.ts:64-73]
7. **Stale or exposed evidence.** Keep timestamps, source names, denominators and environment in the report, but no DB URL, credentials, CRN-level grade buckets, or raw export files. [VERIFIED: AGENTS.md:32-53; .planning/phases/05-mvp1-p2-grade-data-sourcing-import-to-supabase/05-IMPORT-RECORD.md:1-11]

## Code Examples

```bash
# Existing read-only gates, run against the same configured hosted database.
uv run python scripts/validate_tampa_ingest.py --term 202701 --targets config/course_targets.toml
uv run python scripts/check_data_quality.py --term 202701 --json
uv run uvicorn easy_a.api.app:app --host 127.0.0.1 --port 8000 --no-access-log
uv run python scripts/benchmark_rankings_search.py --live --http-base-url http://127.0.0.1:8000 --term 202701 --iterations 50
```

These commands and exact arguments are present in the scripts and prior performance report. Do not paste unredacted JSON findings into a public report; summarize counts, check IDs and failure examples without source credentials or raw grade data. [VERIFIED: scripts/validate_tampa_ingest.py:191-238; src/easy_a/quality/cli.py:16-70; scripts/benchmark_rankings_search.py:85-151; .planning/phases/07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s/07-PERF-REPORT.md:14-31]

## State of the Art

No library migration is indicated. The relevant change is internal: Phase 7 reduced whole-term cache rebuild to 4.77 seconds and quality pass to 2.45 seconds, making a fresh full-term Phase 8 verification practical. The older 2.40-second synthetic search figure is superseded by the dated live 309.91 ms loopback result. [VERIFIED: .planning/STATE.md:44-55; .planning/phases/07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s/07-PERF-REPORT.md:111-122,133-178]

## Assumptions Log

| # | Claim | Risk if wrong |
|---|---|---|
| A1 | [ASSUMED] The Phase 8 execution environment can still reach the hosted Supabase using the project `.env`; this session only verified `.env` exists and did not connect. | Live gates may be NOT MEASURED until connectivity is restored. |
| A2 | [ASSUMED] No new approved historical workbooks for the remaining represented courses have appeared since the dated state report. | The grade gap could be smaller; rerun the live inventory before verdict. |

## Question dispositions and external dependencies

1. **External dependency, unresolved availability:** Approved historical SGDIS exports for the remaining represented courses have not been demonstrated. Existing evidence covers only 10 courses; Phase 8 must quantify the live gap and cannot assume the missing source data exists or silently certify the milestone. Sourcing/import remains necessary before literal MVP-1 completion. [VERIFIED: .planning/STATE.md:35-42,94-98; .planning/phases/05-mvp1-p2-grade-data-sourcing-import-to-supabase/05-IMPORT-RECORD.md:1-33]
2. **Resolved by the controlling project decision:** The milestone's all-sections grade requirement stays literal. `PROJECT.md` controls over the softer Phase 8 criterion unless the user explicitly changes it; a missing course history leaves MVP 1 open. [VERIFIED: .planning/PROJECT.md:23-27; .planning/ROADMAP.md:440-446]
3. **Scope limit recorded:** No deployed host/domain has been supplied. Phase 8 can prove loopback HTTP over hosted Supabase but must mark deployed/browser latency unmeasured. [VERIFIED: .planning/STATE.md:108-112]

## Environment Availability

| Dependency | Needed for | Observation | Fallback |
|---|---|---|---|
| `uv` | Python scripts/tests | Installed, `0.12.17` on 2026-09-23. [VERIFIED: local `uv --version` probe] | None needed. |
| Python | Backend | `uv run python --version` returned `3.14.4`; project declares `>=3.12`, with no declared upper bound. [VERIFIED: local probe; pyproject.toml:1-7] | Use project's established `uv` environment; record runtime in evidence. |
| Node/npm | Frontend tests/build | Node `v24.21.0`, npm `11.19.0` observed. [VERIFIED: local probes] | None needed. |
| Hosted Supabase | Live counts/performance | `.env` exists and dated Phase 7 live run succeeded; current reachability was not probed. [VERIFIED: local file-presence probe; .planning/STATE.md:26-55] | Mark live gates NOT MEASURED if connection fails; do not infer PASS. |
| `EASY_A_TEST_POSTGRES_URL` | PostgreSQL-specific integration suite | Not exported in this shell; default tests skip PostgreSQL cases. [VERIFIED: local environment-presence probe; README.md:717-722] | Provide a dedicated test DB/schema URL when available; report skipped tests. |

## Validation Architecture

`workflow.nyquist_validation` is absent in `.planning/config.json`, so include this strategy. [VERIFIED: .planning/config.json:1-6]

| Property | Value |
|---|---|
| Python framework | pytest; `testpaths = ["tests"]`. [VERIFIED: pyproject.toml:35-38] |
| Frontend framework | Vitest via `npm test`. [VERIFIED: web/package.json:6-12] |
| Quick run | `uv run pytest tests/refresh/test_validate_tampa_ingest.py tests/rankings/test_cache_parity.py tests/api/test_benchmark_rankings_search.py -q`; `npm test -- --run` is unnecessary because script already uses `vitest run`. [VERIFIED: pyproject.toml:35-38; web/package.json:6-12; inspected test files] |
| Full run | `uv run pytest -q`, `uv run ruff check .`, `uv run mypy src migrations scripts tests`, and in `web/`: `npm test`, `npm run lint`, `npm run typecheck`, `npm run build`. [VERIFIED: README.md:500-508; web/package.json:6-12] |

| Requirement | Behavior | Test type/command | Existing? |
|---|---|---|---|
| REQ-COVERAGE-03 | Suffix, target/cache reconciliation and honest fallback | `uv run pytest tests/refresh/test_validate_tampa_ingest.py -q`; live `uv run python scripts/validate_tampa_ingest.py --term 202701` | Yes. [VERIFIED: scripts/validate_tampa_ingest.py:157-238; tests/refresh/test_validate_tampa_ingest.py:1-20] |
| REQ-COVERAGE-03 | Every stored term+CRN appears exactly once across API pages | New focused test/CLI plus live HTTP page scan; compare identity set to stored set | Wave 0 gap. Existing benchmark validates broad total only. [VERIFIED: scripts/benchmark_rankings_search.py:269-272] |
| REQ-GRADES-01 | Source-grade rows, raw totals and course-backed cached sections reconcile, with every missing course enumerated | New read-only full-term inventory CLI + synthetic unit tests for no-history/subject/course cases; live run | Wave 0 gap. Phase 05 record covers 10 courses only. [VERIFIED: .planning/phases/05-mvp1-p2-grade-data-sourcing-import-to-supabase/05-IMPORT-RECORD.md:1-33] |
| REQ-GRADES-01 | Global fallback cannot look like course evidence in API or UI | Existing honest validator + new desktop/mobile component tests for global and subject states | API validator exists; UI tests are a gap. [VERIFIED: scripts/validate_tampa_ingest.py:157-190; web/src/components/RankingTable.tsx:57-97] |
| REQ-PERF-01 | Full-scale HTTP p95 | Live `uv run python scripts/benchmark_rankings_search.py --live --http-base-url http://127.0.0.1:8000 --term 202701 --iterations 50` | Yes. [VERIFIED: scripts/benchmark_rankings_search.py:85-151,243-310] |
| Cross-cutting | Quality errors, warning/info reasons | Live `uv run python scripts/check_data_quality.py --term 202701 --json` | Yes. [VERIFIED: src/easy_a/quality/cli.py:16-70] |

**Sampling:** run focused tests per implementation task; full Python/frontend checks after the final wave; live hosted gates at phase sign-off. A PostgreSQL integration result only counts if the dedicated test URL is provided; otherwise report the skip count. [VERIFIED: .planning/STATE.md:52-55; README.md:717-722]

**Wave 0:** create tests only for the new course-grade inventory, complete API page identity scan, and fallback UI wording; do not duplicate existing validator/benchmark logic. [VERIFIED: scripts/validate_tampa_ingest.py:157-238; scripts/benchmark_rankings_search.py:243-310]

## Security Domain

Security enforcement is not explicitly disabled in `.planning/config.json`. Use OWASP ASVS 5.0.0 numbering; the current official taxonomy lists V2 Validation, V3 Web Frontend, V4 API, V5 File Handling, V6 Authentication, V7 Session Management, V8 Authorization and V11 Cryptography. [VERIFIED: .planning/config.json:1-6; CITED: https://cornucopia.owasp.org/taxonomy/asvs-5.0]

| Applicable ASVS area | Applies? | Phase-specific control |
|---|---|---|
| V2 Validation / V4 API | Yes | Validate term/query arguments and response identity/shape; preserve existing Pydantic and ORM parameter binding. [VERIFIED: scripts/benchmark_rankings_search.py:85-151,217-239; scripts/validate_tampa_ingest.py:191-238] |
| V3 Web Frontend | Yes | Render source and missing-evidence state accurately; escape text through React rendering. [VERIFIED: web/src/components/RankingTable.tsx:57-97; web/src/components/RankingDetails.tsx:12-90] |
| V5 File Handling | No new upload | Do not add workbook handling in a verification-only phase; raw exports remain outside Git. [VERIFIED: AGENTS.md:43-53] |
| V6 Authentication / V7 Session / V8 Authorization | No new capability | The project excludes auth/accounts in MVP 1; avoid adding these flows. [VERIFIED: .planning/PROJECT.md:320-329] |
| V11 Cryptography / V12 Secure Communication | Existing DB connection only | Do not expose URLs/credentials in logs or artifacts; use existing configured hosted connection. [VERIFIED: scripts/benchmark_rankings_search.py:14-19; .planning/phases/07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s/07-PERF-REPORT.md:1-12] |

**Threat patterns:** accidental raw-export publication (information disclosure), misleading fallback evidence (integrity), and report claims based on synthetic or stale state (integrity). Existing safeguards are Git tracked-file inspection, explicit source/effective-N checks, and dated live HTTP/database evidence. [VERIFIED: AGENTS.md:32-53; scripts/validate_tampa_ingest.py:157-190; .planning/phases/07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s/07-PERF-REPORT.md:1-31]

## Sources

### Primary (HIGH confidence)

- Repository's current `AGENTS.md`, `.planning/STATE.md`, `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` and source/test files named above, opened in this session.
- Dated Phase 05 import record, Phase 06 validation summary and Phase 07 performance report, opened in this session. These support historical results; live claims must be remeasured.
- [OWASP ASVS 5.0 taxonomy](https://cornucopia.owasp.org/taxonomy/asvs-5.0) for current security-category names.

### Secondary (MEDIUM confidence)

- None needed for codebase-specific decisions.

## Metadata

**Confidence breakdown:** stack HIGH (repository manifests and local probes); architecture HIGH (opened code); pitfalls HIGH for existing behavior, MEDIUM for current hosted counts until rerun.
**Research date:** 2026-09-23
**Valid until:** 2026-10-23 for code structure; live counts and latency should be rechecked at execution.
