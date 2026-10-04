---
phase: "08"
slug: "mvp1-p5-end-to-end-mvp-1-verification"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-24"
---

# Phase 08 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register authored at plan time (08-01..08-05 `<threat_model>` blocks). ASVS L1: mitigations verified at grep/test depth against the committed implementation. No SUMMARY carried a `## Threat Flags` section.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Gate scripts → hosted Supabase | `verify_rankings_pages.py`, `inventory_tampa_grades.py`, `validate_tampa_ingest.py` read the live DB via the app session factory | DB credentials (from `.env`, never printed); aggregate grade rows (read-only) |
| Gate scripts → local API | Identity scan and p95 benchmark call `GET /api/v1/rankings/search` | Public ranking fields over loopback HTTP only |
| Script output → committed reports | JSON stdout, `08-VERIFICATION-REPORT.md`, `08-D21-EXCEPTIONS.md` | Derived aggregates only; no credentials, URLs or per-CRN grade buckets |
| API → browser UI | Evidence wording rendered from `score_source` / `effective_n` | Already-public aggregate fields |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-08-01 | Tampering | identity verdict in `reconcile()` | high | mitigate | Missing/extra/duplicate/order/boundary checks with named failure reasons; 16 tests in `tests/api/test_verify_rankings_pages.py` | closed |
| T-08-02 | Denial of service | `scan_pages()` | medium | mitigate | `MAX_PAGE_SIZE = 200` (scripts/verify_rankings_pages.py:50); bounded page count; one term per run | closed |
| T-08-03 | Information disclosure | identity-scan JSON stdout | high | mitigate | Sanitized `_environment_label` (verify_rankings_pages.py:301); no grade rows read | closed |
| T-08-13 | Spoofing | `--http-base-url` | medium | mitigate | Plain-loopback-origin validation rejects non-loopback hosts, credentials, path/query (verify_rankings_pages.py:278-290) | closed |
| T-08-04 | Tampering | `classify_section()` | high | mitigate | One state per section; evidence_backed requires attributed letter-grade rows + raw-total reconciliation; failure states block D-21 PASS; 22+ inventory tests | closed |
| T-08-05 | Information disclosure | inventory JSON / `--exceptions-md` | high | mitigate | Derived aggregates only; test rejects bucket keys in JSON; `08-D21-EXCEPTIONS.md` has no bucket columns | closed |
| T-08-06 | Repudiation | provenance reconciliation | medium | mitigate | `source_hash_count`, `ingested_at_min/max`, historical term recorded (inventory_tampa_grades.py:151-153); UTC window in report | closed |
| T-08-14 | Elevation of privilege (guard bypass) | `assert_honest_coverage()` | high | mitigate | Accepts only `course`/`effective_n == 0` with stored A–F sum 0 and total > 0 (validate_tampa_ingest.py:256); four negative tests; fabricated-row test unchanged | closed |
| T-08-15 | Denial of service | `collect_inventory()` | low | mitigate | Fixed statement count test (`test_term_batch_statement_count_does_not_grow_with_represented_courses`) | closed |
| T-08-07 | Tampering (misleading evidence) | `describeEvidence()`, RankingTable, RankingDetails | high | mitigate | Exact-string positive/negative assertions per scope in `RankingEvidence.test.tsx`; unknown sources fail closed (rankings.ts:114,152); human UAT passed 2026-09-24 | closed |
| T-08-08 | Information disclosure | source label rendering | low | accept | React text escaping; only public aggregate fields; no new fields | closed |
| T-08-16 | Tampering (scope creep into scoring) | web/src/types, web/src/api, backend | medium | mitigate | `git diff 35da18b -- src web/src/types web/src/api web/src/fixtures` empty (D-02) | closed |
| T-08-09 | Tampering | MVP-1 verdict | high | mitigate | Verdict derived from gate rows; evidence-backed and exception counts separate; machine-generated exception list | closed |
| T-08-10 | Information disclosure | `08-VERIFICATION-REPORT.md`, `08-D21-EXCEPTIONS.md` | high | mitigate | No connection-string/password substrings found in either file; no tracked `.xlsx`/`.csv` (D-19) | closed |
| T-08-11 | Repudiation | live evidence | medium | mitigate | UTC window, commands, denominators and before/after snapshot comparison recorded in the report | closed |
| T-08-12 | Denial of service | benchmark | low | accept | Existing bounded 50-request loopback harness, single term | closed |
| T-08-17 | Tampering | hosted data | medium | mitigate | Read-only: `REPEATABLE READ READ ONLY` transaction (inventory_tampa_grades.py:637); no rebuild/import/write in any 08 plan | closed |
| T-08-05-01 | Tampering (false-PASS integrity verdict) | `Inventory.to_dict` | high | mitigate | `integrity_ok = failure_section_count == 0 and not any(integrity.values())` (inventory_tampa_grades.py:228); invariant test over every reported counter | closed |
| T-08-05-02 | Tampering (production data) | 08-05 live re-verification | high | mitigate | Read-only transaction; validator issues SELECTs only; no `--exceptions-md` regeneration | closed |
| T-08-05-03 | Information disclosure | inventory JSON, report edits | medium | mitigate | JSON kept outside the repo; report records derived aggregates; sanitized environment label | closed |
| T-08-05-04 | Tampering (validation weakened) | `assert_suffix_exact_ingest` | medium | mitigate | Raise condition/queries/loop unchanged (verified by 08-05 acceptance + re-verification); new cross-term tests | closed |
| T-08-05-05 | Tampering (stale cache hidden/false) | `stale_cache` | medium | mitigate | `evidence_grade_ingested_at_max` uses scoring-window rows only (inventory_tampa_grades.py:168,244); tests pin both directions | closed |
| T-08-05-06 | Information disclosure | `git fetch origin main` (D-10) | low | accept | Updates remote-tracking refs only; no credential printed | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-08-01 | T-08-08 | React escapes rendered text; only already-public aggregate fields are shown; no new fields introduced | Plan 08-03 threat model | 2026-09-23 |
| AR-08-02 | T-08-12 | Benchmark is a bounded 50-request loopback run against one term | Plan 08-04 threat model | 2026-09-23 |
| AR-08-03 | T-08-05-06 | `git fetch` only updates remote-tracking refs; nothing secret is output | Plan 08-05 threat model | 2026-09-24 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-24 | 23 | 23 | 0 | secure-phase orchestrator (ASVS L1, plan-time register; grep/test evidence) |

## Security Audit 2026-09-24
| Metric | Count |
|--------|-------|
| Threats found | 23 |
| Closed | 23 |
| Open | 0 |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-24
