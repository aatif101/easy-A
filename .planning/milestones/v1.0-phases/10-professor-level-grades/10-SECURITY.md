---
phase: "10"
slug: professor-level-grades
status: verified
threats_open: 0
asvs_level: 1
created: "2026-10-04"
---

# Phase 10 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Audited at HEAD 22234da; code equals origin/main 6a81e29. Auditor: gsd-security-auditor (block_on: high).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Scoring code -> public rankings | Constants decide every published easiness score | Scores |
| USF StaffScheduleSearch -> backfill | Untrusted HTML parsed into production rows | Historical sections, instructor names |
| Operator workstation -> hosted Supabase | Read-only measurement; one reviewed production write (apply) | Section, instructor and ranking rows |
| Operator workstation -> USF | Whole-term requests, paced | Schedule HTML |
| Backfill CLI <-> live sync worker | Two writers to section_rankings | Ranking cache |
| Public API JSON -> browser DOM | Instructor names and figures rendered to students | Names, grade shares |
| Tool output / owner reply -> committed planning evidence | Figures and decisions become authoritative records | Counts, CRNs, decisions |

---

## Threat Register

All dispositions are mitigate. Evidence (file:line, tests) is in the audit report summarised below; every threat verified present.

| Threat ID | Category | Component | Severity | Mitigation | Status |
|-----------|----------|-----------|----------|------------|--------|
| T-10-01 | Tampering | scoring defaults / course-level scores | high | Exact-equality invariance test; per-source strengths; real-data diff exit 0 | closed |
| T-10-02 | Repudiation | methodology change | medium | PROJECT.md D-24/D-02, README subsection | closed |
| T-10-03 | Tampering | live 202701 data | high | argparse term allowlist; isolation tests | closed |
| T-10-04 | DoS (USF) | USF requests | medium | 10 s floor, no retry, no per-subject fallback | closed |
| T-10-05 | Tampering | section_instructors duplicates | high | Change-only append; idempotent re-run test | closed |
| T-10-06 | Info disclosure | CLI output / errors | medium | `_scrub`/`_redact`, no "://" assertions (see residual WR-02) | closed |
| T-10-07 | Tampering | course-level history | high | Unattributed/mismatched rows skipped and counted | closed |
| T-10-08 | Info disclosure | diff and pair JSON | medium | CRNs, course keys, numbers only; tests | closed |
| T-10-09 | Tampering | hosted database | medium | REPEATABLE READ READ ONLY, no writes | closed |
| T-10-10 | Repudiation | D-04 gate verdict | high | Verdict and exit code derived from reported fields | closed |
| T-10-11 | Spoofing | Staff-section list | high | Heading/explainer copy, no pin, no "Used in" | closed |
| T-10-12 | Tampering (XSS) | instructor names in DOM | medium | React text children only | closed |
| T-10-13 | Info integrity | fallback rankings | high | Gated on course_history scope and non-null breakdown | closed |
| T-10-14 | Tampering | breakdown vs scoring | high | Shared `_instructor_course_stats`; iff and parity tests | closed |
| T-10-15 | Info integrity | breakdown for fallback courses | high | Builder returns None unless history and mapped instructors | closed |
| T-10-16 | DoS | search payload size | medium | Only rows >= 15 plus current serialized; p95 273 ms | closed |
| T-10-17 | Tampering | dry run | high | Always rolls back; tests | closed |
| T-10-18 | Tampering (race) | section_rankings | high | `try_sweep_lock` first statement | closed |
| T-10-19 | Tampering | apply differs from review | high | `--expect-inserted` and invariant gate roll back (see residual WR-03) | closed |
| T-10-20 | Tampering (destructive) | rollback | high | Preview default, `--yes`, allowlisted terms, eligibility rules | closed |
| T-10-21 | Tampering | hosted DB during review | high | Read-only recon; identical before/after counts | closed |
| T-10-22 | Info disclosure | evidence and what-if JSON | medium | Negative greps clean; raw USF pages git-ignored | closed |
| T-10-23 | DoS (USF) | USF requests | medium | Code controls verified; 20 requests vs 5 planned, each owner-authorised (deviation) | closed |
| T-10-24 | Tampering | hosted database write | high | D-04 approve before apply; gates; read-only verify | closed |
| T-10-25 | Elevation of privilege | unreviewed code live | high | CI green; post-deploy diff exit 0 | closed |
| T-10-26 | Info disclosure | evidence and apply report | medium | Counts and identifiers only (see residual WR-02) | closed |
| T-10-27 | Repudiation | recovery | medium | Rollback and rebuild-only documented and tested | closed |
| T-10-28 | Repudiation | STATE.md facts | medium | Cited figures; REQ-PROF-01 unticked until verified | closed |
| T-10-29 | Spoofing | deployed instructor block | medium | Bundle copy check; UAT 9/9 pass | closed |
| T-10-30 | Spoofing | empty-state gate | medium | isEmpty requires othersCount === 0; regression test | closed |
| T-10-31 | Tampering | locked UI copy drift | low | Copy appears in UI-SPEC; no const lines changed | closed |
| T-10-32 | Repudiation | SC1 owner decision | high | Blocking-human gate; override fields recorded (accepted_at time-of-day is a placeholder) | closed |
| T-10-33 | Tampering | figure integrity | medium | Every figure appears in evidence file | closed |
| T-10-34 | DoS | UAT 7 scan | low | Operator-run, own API, paced | closed |
| T-10-35 | Info disclosure | UAT 7 evidence | low | Counts and CRNs only | closed |
| T-10-SC (x11) | Tampering | package installs, plans 10-01..10-11 | high | No manifest, lockfile, Dockerfile or render.yaml change across the phase | closed |

*Status: open · closed · open — below high threshold (non-blocking)*

---

## Accepted Risks Log

No accepted risks. The following known residuals are recorded for awareness, not accepted by anyone; both sit beside present, verified mitigations and do not affect `threats_open`:

| Residual | Maps to | Note |
|----------|---------|------|
| P10-WR-02 | T-10-06, T-10-26 | `_scrub` strips `scheme://` only; a DB error naming host/IP/role could reach stdout or `--report-json`. No leak in committed artifacts. Fix before any backfill re-run. |
| P10-WR-03 | T-10-19 | A wrong `--rebuild-term` gives a vacuous invariant and a stale cache; no empty-cache guard. `--expect-inserted` is a second gate. Fix before any backfill re-run. |
| Unregistered flag | 10-07 | `--save-responses` writes raw USF pages locally; confined to git-ignored `failed-responses/`, mode 0600, 0 tracked. |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-04 | 46 (35 + 11 T-10-SC) | 46 | 0 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-04
