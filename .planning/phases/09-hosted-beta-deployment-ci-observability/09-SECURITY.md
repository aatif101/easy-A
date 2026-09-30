---
phase: "09"
slug: hosted-beta-deployment-ci-observability
status: verified
threats_open: 0
asvs_level: 1
created: "2026-09-30"
---

# Phase 09 - Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Worker to USF | Whole-term schedule request and paced catalog lookups | Public schedule HTML |
| Worker/API to hosted Supabase | Sweep transaction, reads for API | DATABASE_URL secret; student-facing section data |
| Operator to hosted Supabase | Manual migration 0004 | MIGRATION_DATABASE_URL secret (operator shell only) |
| Browser to API | Public search and /sync-status | Public data, fixed error-kind tokens |
| GitHub Actions to Render | checksPass auto-deploy | Code, no secrets in CI |
| Repository to container image | Docker build context | Source only; .env excluded |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-09-01 | Tampering | ci.yml action refs | high | mitigate | Actions pinned by tag (setup-uv@v10.2.0, checkout@v7, setup-node@v7), asserted in tests/test_ci_workflow.py | closed |
| T-09-02 | Elevation of Privilege | workflow GITHUB_TOKEN | medium | mitigate | permissions: contents: read; pull_request trigger; no secrets | closed |
| T-09-03 | Denial of Service | Render checksPass gate | medium | mitigate | No path filters; cancel-in-progress false on main | closed |
| T-09-04 | Tampering | section_rankings cache | medium | mitigate | Cache rows for removed sections deleted and never recreated (rankings/cache.py, sync/apply.py) | closed |
| T-09-05 | Tampering | hosted schema migration 0004 | high | mitigate | Upgrade and downgrade, CI round-trip on postgres:16, operator-applied | closed |
| T-09-06 | Information Disclosure | SchemaNotCurrentError message | low | mitigate | Fixed message, no URL or driver text (schema_guard.py) | closed |
| T-09-07 | Denial of Service | cadence rules | high | mitigate | Upward-only jitter, tier floors, backoff floor, randomized invariant test (sync/windows.py) | closed |
| T-09-08 | Tampering | registration_windows.toml | medium | mitigate | extra=forbid, https usf.edu sources, ordered and disjoint; invalid file exits 4 | closed |
| T-09-09 | Denial of Service | restart/deploy churn | medium | mitigate | Floor seeded from latest IngestRun; live restart confirmed | closed |
| T-09-10 | Tampering | fetch.parse_whole_term and gate | high | mitigate | Header fail-closed, td-row-count check, gate before any write | closed |
| T-09-11 | Denial of Service | search_term body size | medium | mitigate | Content-Type check, 25 MB streaming cap, chunked parse | closed |
| T-09-12 | Tampering | concurrent sweeps | high | mitigate | pg_try_advisory_xact_lock; CI fails if Postgres tests skip | closed |
| T-09-13 | Spoofing | USF request identity | low | accept | Identifying User-Agent; accepted per PROJECT.md D-22(d) | closed |
| T-09-14 | Tampering | seat freshness label | medium | mitigate | Judged from max(verified_at, observed_at) against cadence thresholds | closed |
| T-09-15 | Tampering | env overrides | low | mitigate | Both overrides required; bounds validated | closed |
| T-09-16 | Information Disclosure | /sync-status | high | mitigate | Only SYNC_ERROR_KINDS tokens returned; raw error_message never serialized | closed |
| T-09-17 | Information Disclosure | request log line | medium | mitigate | Route template or "unmatched" only; no query or raw path | closed |
| T-09-18 | Denial of Service | /sync-status cost | low | mitigate | Three bounded queries; term pattern-constrained | closed |
| T-09-19 | Tampering | API on stale schema | medium | mitigate | Lifespan schema guard; health check | closed |
| T-09-20 | Tampering | coverage/quality/refresh counts | medium | mitigate | removed_at IS NULL across all consumers, with tests | closed |
| T-09-21 | Repudiation | legacy ingest restoring sections | low | mitigate | removed_at cleared on update; tested | closed |
| T-09-22 | Tampering | partial or poisoned sweep | high | mitigate | Single transaction, gate before writes, reversible removals | closed |
| T-09-23 | Information Disclosure | IngestRun.error_message | medium | mitigate | URLs stripped, capped at 500 chars (regex covers postgres URLs only; see flags) | closed |
| T-09-24 | Repudiation | unrecorded sweeps | low | mitigate | Success and failure both recorded as IngestRun rows | closed |
| T-09-25 | Denial of Service | DB round trips, cache rebuild | medium | mitigate | Bulk reads, chunked updates, rebuild only on structural change | closed |
| T-09-26 | Tampering (XSS) | SyncStatus rendering | low | mitigate | No innerHTML; React text; strict timestamp parse | closed |
| T-09-27 | Spoofing | synthetic/mock freshness | medium | mitigate | Synthetic mode never shows "Updated"; explicit never-verified state | closed |
| T-09-28 | Information Disclosure/SSRF | benchmark --remote-url | medium | mitigate | https-only plain origin, no redirects, no proxy env, exception class only | closed |
| T-09-29 | Tampering | coverage/D-21 accounting | medium | mitigate | Untargeted course allowed only if all sections Tampa undergraduate | closed |
| T-09-30 | Denial of Service | restart/manual vs D-22 floor | high | mitigate | --once/--dry-run refuse inside floor (exit 3); loop seeded from DB | closed |
| T-09-31 | Tampering | SIGTERM mid-sweep | medium | mitigate | Stop event only interrupts sleeps; single transaction; live confirmation | closed |
| T-09-32 | Information Disclosure | worker logs | medium | mitigate | Typed fields only; URL scrub in formatter | closed |
| T-09-33 | Elevation of Privilege | --max-missing-fraction | low | mitigate | Rejected outside --once/--dry-run; loop passes no override | closed |
| T-09-34 | Denial of Service | CourseAdder | high | mitigate | 10 per sweep, 2 s pacing, 6 h negative cache, not on dry-run | closed |
| T-09-35 | Tampering | catalog page to Course | medium | mitigate | Exact (subject, number) match; fixed host; no stand-in rows | closed |
| T-09-36 | Spoofing | catalog request identity | low | accept | Identifying User-Agent; accepted per PROJECT.md D-22(d) | closed |
| T-09-37 | Information Disclosure | image layers/build context | high | mitigate | .dockerignore excludes .env*; CI asserts no /app/.env | closed |
| T-09-38 | Information Disclosure | render.yaml | high | mitigate | DATABASE_URL sync: false; no MIGRATION_DATABASE_URL; tested | closed |
| T-09-39 | Elevation of Privilege | container user | medium | mitigate | USER 10001; CI asserts uid not 0 | closed |
| T-09-40 | Spoofing | CORS | medium | mitigate | allow_credentials False, GET only, origins from env | closed |
| T-09-41 | Tampering | deploys of unverified commits | medium | mitigate | autoDeployTrigger checksPass on all services; docker CI job | closed |
| T-09-42 | Tampering | hosted schema | high | mitigate | Operator applied 0004; read-only verification recorded (offline --sql review not separately evidenced) | closed |
| T-09-43 | Information Disclosure | evidence/checkpoint output | medium | mitigate | Negative greps clean across evidence, runbook, UAT, verification | closed |
| T-09-44 | Denial of Service | real-data dry run | low | mitigate | Exactly one dry run; earliest Blueprint time recorded | closed |
| T-09-45 | Tampering | merge of unverified code | medium | mitigate | PR #33 merged after python, web and docker green with Postgres tests executed | closed |
| T-09-46 | Information Disclosure | Render env/dashboard | high | transfer | Transferred to Render access controls; secrets sync: false only | closed |
| T-09-47 | Spoofing | CORS origin | medium | mitigate | Live probe returned exact web origin | closed |
| T-09-48 | Denial of Service | worker memory/OOM | medium | mitigate | Chunked parse, import-hygiene test, CI RSS guard; peak 194-223 MB self-reported | closed |
| T-09-49 | Denial of Service | hosted sweep cadence | high | mitigate | Blueprint created after earliest time; post-restart sleep honoured floor | closed |
| T-09-50 | Repudiation | go-live facts | low | mitigate | Every probe dated in 09-ROLLOUT-EVIDENCE.md | closed |
| T-09-51 | Elevation of Privilege | gate_thresholds / run_sweep default | high | mitigate | gate_thresholds(None) returns defaults; loop passes no override; tested | closed |
| T-09-52 | Tampering | override on truncated response | medium | mitigate | zero_rows never overridable; runbook warns against overriding on truncation | closed |
| T-09-53 | Repudiation | who applied an override | low | accept | Accepted: runbook Run Log records each override; none logged yet | closed |
| T-09-54 | Information Disclosure | gate reasons/help/test output | low | mitigate | Reasons carry counts and subject codes only | closed |
| T-09-55 | Denial of Service | gate blocked after real mass drop | medium | mitigate | Override now covers row_floor and subjects_absent; tested | closed |
| T-09-56 | Tampering | float rounding at threshold | low | mitigate | Exact Fraction arithmetic; 0.7 boundary tested | closed |
| T-09-57 | Tampering | redeploy with changed gate code | medium | mitigate | PR #35 merged only after CI success; loop has no override path | closed |
| T-09-SC | Tampering | npm/pip/cargo installs | high | mitigate | Dependency manifests and lockfiles unchanged in phase 9; lockfile installs only | closed |

*Status: open, closed, or open below block_on threshold (non-blocking). 58 threats: high 16, medium 28, low 14; all closed.*
*Verification method: static review of each mitigation in code and config by the security auditor (ASVS L1, block_on high), plus 55 offline tests (test_gate, test_ci_workflow, test_deploy_config, test_schema_guard). No network calls were made by the audit.*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-09-01 | T-09-13, T-09-36 | Requests to USF carry an identifying User-Agent; spoofing risk accepted per locked decision D-22(d) in PROJECT.md | Plan-time decision (PROJECT.md D-22(d)); not individually re-confirmed in this file | 2026-09-30 |
| AR-09-02 | T-09-53 | Overrides are attributed only through the runbook Run Log, not enforced by the tool | Plan-time decision (09-16-PLAN threat model); not individually re-confirmed in this file | 2026-09-30 |
| TR-09-01 | T-09-46 | Transferred to Render access controls; secrets are sync: false only, never in the repository | Plan-time decision (09-15-PLAN threat model); not individually re-confirmed in this file | 2026-09-30 |

*Accepted risks do not resurface in future audit runs.*

---

## Non-blocking flags from the audit (all already open in 09-REVIEW.md / 09-REVIEW-DISPOSITION.md)

1. **WR-03 (medium): cross-process cadence-floor race.** The floor is not re-read from the database inside the locked transaction, so during Render's 60-90 s old/new worker overlap a second whole-term request could land inside the D-22(b) floor. Declared controls for T-09-07, T-09-09, T-09-30 and T-09-49 exist, so they are closed, but this would fail a placement check at ASVS L2. Suggested fix: re-check the floor inside the locked transaction.
2. **WR-04 (low): dry runs are unrecorded** and so not floor-limited; documented in the runbook.
3. **WR-02 (low-medium): no wall-clock cap on the whole-term fetch**; a slow-drip response could hold the advisory lock. Rolls back cleanly; availability only.
4. **IN-01 (low): error-text scrub covers only postgres URLs**; driver errors can put host or project-ref text into Render logs and ingest_runs.error_message. /sync-status never exposes it; no password leak found.
5. **WR-01 (low): log formatter can corrupt failed-sweep JSON lines** (over-redacts, does not leak).
6. **WR-07/WR-08 (low): search has no removed_at guard** and the legacy restore does not rebuild the cache; the invariant holds today.
7. **IN-04 (low): actions pinned by tag, not SHA.** Mitigated by read-only token and no secrets.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-30 | 58 | 58 | 0 | gsd-security-auditor (static, ASVS L1) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-30 by automated audit. The operator has not separately signed off on the three accepted/transferred risks above.
