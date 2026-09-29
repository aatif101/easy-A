---
phase: "09"
slug: hosted-beta-deployment-ci-observability
status: draft
nyquist_compliant: true
wave_0_complete: false
created: "2026-09-29"
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Full requirement→test map lives in `09-RESEARCH.md` § Validation Architecture; the planner fills the per-task map below.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.3.0 (Python), vitest ^3.2.4 (web) |
| **Config file** | `pyproject.toml` (`testpaths = ["tests"]`); `web/vite.config.ts` |
| **Quick run command** | `uv run pytest tests/sync tests/schedule tests/api -q -x` |
| **Full suite command** | `uv run pytest -q` and `npm --prefix web test` |
| **Estimated runtime** | ~25 seconds (8 s Python + 16 s web) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/sync -q -x` (plus `npm --prefix web test` for UI tasks)
- **After every plan wave:** `uv run pytest -q`, `uv run ruff check .`, `uv run mypy src`, `npm --prefix web run lint && npm --prefix web run typecheck && npm --prefix web test && npm --prefix web run build`
- **Before `/gsd-verify-work`:** Full suite must be green (CI included)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-T1 | 01 | 1 | REQ-OPS-01 | T-09-01, T-09-03 | Exact action pins; no path filters; PostgreSQL tests may not skip in CI | lint + structural | `uv run ruff check .` · `uv run pytest tests/test_ci_workflow.py -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-01-T2 | 01 | 1 | REQ-OPS-01 | T-09-02 | Read-only token, no secrets; mypy report-only (D-12) | structural + web gates | `uv run pytest tests/test_ci_workflow.py -q` · `npm --prefix web run lint && npm --prefix web run typecheck && npm --prefix web test` | ✅ (T1) | ⬜ pending |
| 09-02-T1 | 02 | 1 | REQ-SYNC-01 | T-09-04, T-09-05 | Removed section leaves cache and search; migration offline only | unit (SQLite) + offline SQL | `uv run pytest tests/rankings/test_removed_sections.py tests/rankings -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-02-T2 | 02 | 1 | REQ-SYNC-01 | T-09-06 | /section 404 and /course excludes removed; guard message has no URL | API test | `uv run pytest tests/api/test_rankings_api.py tests/test_schema_guard.py tests/rankings -q` | extend + ❌ W0 | ⬜ pending |
| 09-03-T1 | 03 | 1 | REQ-SYNC-01 | T-09-07, T-09-08 | Tier floors never violated; windows config validated | unit (pure, injected clock) | `uv run pytest tests/sync/test_windows.py -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-03-T2 | 03 | 1 | REQ-SYNC-01 | T-09-09 | Floor honoured across restarts; prompt SIGTERM stop | unit | `uv run pytest tests/sync/test_runner.py tests/sync/test_windows.py -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-04-T1 | 04 | 2 | REQ-SYNC-01 | T-09-10, T-09-11 | Fail-closed chunked parse; size and content-type caps; D-04 scope | unit (MockTransport) | `uv run pytest tests/sync/test_fetch.py tests/schedule/test_client.py tests/schedule/test_parser.py -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-04-T2 | 04 | 2 | REQ-SYNC-01 | T-09-10, T-09-12 | Gate thresholds; xact advisory lock exclusion | unit + PostgreSQL integration | `uv run pytest tests/sync/test_gate.py tests/sync/test_lock_postgres.py -q -rs` | ❌ W0 (created in task) | ⬜ pending |
| 09-05-T1 | 05 | 2 | REQ-SYNC-01 | T-09-14 | Freshness from verified time with cadence thresholds | unit + route | `uv run pytest tests/rankings/test_verified_freshness.py tests/refresh/test_targets.py tests/rankings tests/api -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-05-T2 | 05 | 2 | REQ-SYNC-01 | T-09-15 | Override precedence; legacy 600/1800 frozen | unit | `uv run pytest tests/schedule/test_freshness.py tests/refresh/test_targets.py -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-06-T1 | 06 | 2 | REQ-OPS-01, REQ-SYNC-01 | T-09-16, T-09-18 | /sync-status never returns raw error text | API test | `uv run pytest tests/api/test_sync_status.py -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-06-T2 | 06 | 2 | REQ-OPS-01 | T-09-17, T-09-19 | Request log uses route template only; schema guard at startup | unit (caplog) | `uv run pytest tests/api/test_request_logging.py tests/api -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-07-T1 | 07 | 3 | REQ-SYNC-01 | T-09-20, T-09-21 | Coverage counts active only; legacy re-ingest restores | unit | `uv run pytest tests/refresh/test_removed_section_consumers.py tests/schedule/test_ingest.py tests/refresh -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-07-T2 | 07 | 3 | REQ-SYNC-01 | T-09-20 | Current-term listings only; scoring untouched (D-02) | unit + diff guard | `uv run pytest tests/analytics tests/refresh tests/rankings/test_cache_parity.py -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-07-T3 | 07 | 3 | REQ-SYNC-01 | T-09-20 | Quality ignores removed; stale check from verified time | unit | `uv run pytest tests/quality -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-08-T1 | 08 | 3 | REQ-SYNC-01 | T-09-22, T-09-25 | One request, one transaction, IngestRun recorded | E2E (SQLite + MockTransport) | `uv run pytest tests/sync/test_sweep.py -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-08-T2 | 08 | 3 | REQ-SYNC-01 | T-09-25 | Change-only writes; rebuild only on structural change | unit | `uv run pytest tests/sync/test_diff_apply.py tests/sync/test_sweep.py -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-08-T3 | 08 | 3 | REQ-SYNC-01 | T-09-22, T-09-23, T-09-24 | Rollback on every failure kind; sanitized error; dry run writes nothing | unit | `uv run pytest tests/sync/test_sweep_failures.py tests/sync/test_dry_run.py tests/sync -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-09-T1 | 09 | 3 | REQ-SYNC-01 | T-09-26, T-09-27 | Text-only rendering; honest never/error/synthetic states | vitest | `npm --prefix web test -- src/components/SyncStatus.test.tsx` | ❌ W0 (created in task) | ⬜ pending |
| 09-09-T2 | 09 | 3 | REQ-SYNC-01 | T-09-27 | Stale warning appears while the page is open | vitest + build | `npm --prefix web test` | ✅ (T1) | ⬜ pending |
| 09-10-T1 | 10 | 4 | REQ-OPS-01 | T-09-28 | Remote benchmark https-only, no credentials, no redirects | unit | `uv run pytest tests/api/test_benchmark_rankings_search.py tests/api/test_verify_rankings_pages.py -q` | extend existing | ⬜ pending |
| 09-10-T2 | 10 | 4 | REQ-OPS-01, REQ-SYNC-01 | T-09-29 | Auto-added allowed only in sync scope; D-21 exceptions honest | unit | `uv run pytest tests/refresh/test_validate_tampa_ingest.py tests/refresh/test_inventory_tampa_grades.py -q` | extend existing | ⬜ pending |
| 09-11-T1 | 11 | 4 | REQ-SYNC-01 | T-09-30, T-09-32 | Floor refusal (exit 3); no connection URL in logs | CLI unit | `uv run pytest tests/sync/test_cli.py -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-11-T2 | 11 | 4 | REQ-SYNC-01 | T-09-30, T-09-31, T-09-33 | Clean SIGTERM stop; restart floor; import hygiene | unit + subprocess | `uv run pytest tests/sync/test_cli.py tests/sync/test_import_hygiene.py tests/sync -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-12-T1 | 12 | 4 | REQ-SYNC-01 | T-09-34, T-09-35 | Exact-match catalog upsert; honest fallback label | E2E unit | `uv run pytest tests/sync/test_courses.py tests/sync -q` | ❌ W0 (created in task) | ⬜ pending |
| 09-12-T2 | 12 | 4 | REQ-SYNC-01 | T-09-34 | Pacing, cap, negative cache; dry run never fetches | unit | `uv run pytest tests/sync/test_courses.py tests/sync/test_dry_run.py -q` | ✅ (T1) | ⬜ pending |
| 09-13-T1 | 13 | 5 | REQ-OPS-01 | T-09-37, T-09-38, T-09-39, T-09-41 | No secrets in image or Blueprint; non-root; checksPass | structural + CLI validate | `uv run pytest tests/test_deploy_config.py tests/test_ci_workflow.py -q` · `render blueprints validate render.yaml -o text \| grep -q '"valid": true'` | ❌ W0 (created in task) | ⬜ pending |
| 09-13-T2 | 13 | 5 | REQ-OPS-01 | T-09-38 | Env-group answer from the real workspace | checkpoint:human-verify | manual (dashboard) + validator output | n/a | ⬜ pending |
| 09-13-T3 | 13 | 5 | REQ-OPS-01 | T-09-38, T-09-40 | Runbook covers every required operator topic | structural | `uv run pytest tests/test_deploy_config.py -q` + runbook topic grep loop | ❌ W0 (created in task) | ⬜ pending |
| 09-14-T1 | 14 | 6 | REQ-SYNC-01 | T-09-42 | Migration applied only on blocking-human go-ahead | checkpoint:human-action | read-only `uv run alembic current` + information_schema check | n/a | ⬜ pending |
| 09-14-T2 | 14 | 6 | REQ-SYNC-01, REQ-OPS-01 | T-09-43, T-09-44 | Real-data dry run read-only; no secrets in evidence | live (read-only) | evidence heading check + negative grep for connection strings | ❌ W0 (created in task) | ⬜ pending |
| 09-14-T3 | 14 | 6 | REQ-OPS-01 | T-09-45 | Merge only on green CI with PostgreSQL tests executed | checkpoint:human-action | `gh pr checks <n>` · `gh run view <id> --log` | n/a | ⬜ pending |
| 09-15-T1 | 15 | 7 | REQ-OPS-01 | T-09-46, T-09-47 | Exact CORS origin; secrets only in Render | checkpoint:human-action | `curl -fsS <API>/health` + Origin-header probe | n/a | ⬜ pending |
| 09-15-T2 | 15 | 7 | REQ-OPS-01, REQ-SYNC-01 | T-09-48, T-09-49, T-09-50 | Hosted probes read-only; p95 measured | live | evidence heading check · `benchmark_rankings_search.py --remote-url` | ✅ (09-14) | ⬜ pending |
| 09-15-T3 | 15 | 7 | REQ-SYNC-01 | T-09-48 | Change-only soak; memory within 512 MB | checkpoint:human-verify | read-only soak queries after approval | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/sync/__init__.py` and `tests/sync/test_*.py` — REQ-SYNC-01 (package init in 09-03-T1; each test file is created by the task that implements it)
- [ ] Synthetic whole-term fixture generator (never commit the real 7 MB response): `tests/sync/wholeterm_html.py`, 09-04-T1
- [ ] Fix E501 at `scripts/refresh_all_tampa.py:150` and `src/easy_a/refresh/cleanup.py:496` so `ruff check .` is green: 09-01-T1
- [ ] Prove the 3 skipped Postgres tests (plus the new `tests/sync/test_lock_postgres.py`) against `postgres:16`: the CI no-skip step from 09-01-T1, proven on the first CI run in 09-14-T3
- [ ] `web/src/components/SyncStatus.test.tsx` — REQ-SYNC-01: 09-09-T1

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hosted beta reachable, serves real data, "Updated N min ago" advances, Staff→named appears within one cadence interval | REQ-OPS-01 / REQ-SYNC-01 | Needs deployed hosts | 09-15-T2 automated hosted probes + 09-15-T3 soak checkpoint |
| Dockerfile builds and 512 MB worker fits | REQ-OPS-01 | Docker unavailable locally | CI `docker` job (09-13-T1, first run in 09-14-T3); Render Metrics during 09-15-T3 |
| Render env group `easy-a-shared` exists (Open Question 1) | REQ-OPS-01 | Dashboard-only fact; CLI validator disagrees with STATE.md | 09-13-T2 blocking-human checkpoint |
| Migration 0004 applied to hosted Supabase | REQ-SYNC-01 | Requires explicit operator go-ahead | 09-14-T1 blocking-human checkpoint; read-only verification afterwards |
| Blueprint creation and secret entry | REQ-OPS-01 | Secrets come from the user via the Render dashboard | 09-15-T1 blocking-human checkpoint |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (checkpoint tasks carry executor-run read-only verification)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (each new test file is created by the task that needs it)
- [x] No watch-mode flags in test commands (`gh pr checks --watch` in 09-14-T3 is CI monitoring, not a test runner)
- [x] Feedback latency < 30s for per-task commands (full suites about 25 s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
