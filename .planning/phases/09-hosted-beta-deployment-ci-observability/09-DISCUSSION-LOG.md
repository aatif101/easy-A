# Phase 9: Hosted Beta — Deployment, CI, Observability - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-29
**Phase:** 09-hosted-beta-deployment-ci-observability
**Areas discussed:** Sync cadence & scope, First live sync rollout (Failure alerts & freshness UI and CI gates & deploy trigger were delegated to Claude's lean)

---

## Sync cadence & scope

The user pointed to the USF registration-times page for window dates. They asked what "6,663 rows" means and whether Easy-A is missing Tampa classes. Claude's explanation: the tracked list came from the undergraduate catalog, and the gap is most likely graduate or non-catalog courses. It is unmeasured, and rows are not necessarily distinct CRNs. The user's instinct was to add the missing classes.

| Option | Description | Selected |
|--------|-------------|----------|
| Nov 2 → end of drop/add | One window covering registration through drop/add | |
| Nov 2 → Nov 30 only | Priority registration dates only | |
| Several windows | Nov 2–30, Jan 7 state employees, drop/add week; hourly between | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| All Tampa courses | Include graduate courses | |
| Undergrad only | Add missing courses below the 5000 level | ✓ |
| Measure first, then decide | Dry-run the gap before deciding | |

| Option | Description | Selected |
|--------|-------------|----------|
| Worker auto-adds each sweep | New undergrad Tampa courses created automatically | ✓ |
| One-time list expansion | Regenerate course_targets.toml once | |

| Option | Description | Selected |
|--------|-------------|----------|
| Every 5 min | D-22 floor | ✓ |
| Every 10 min | Half the USF load | |

---

## First live sync rollout

The user asked why the first sweep removes ~92 sections and changes instructors. Claude's explanation: this is real USF drift since the 2026-09-20..22 snapshot, which nothing has refreshed since.

| Option | Description | Selected |
|--------|-------------|----------|
| Dry run, I review, then enable | Human-reviewed dry-run gate before writes | |
| Just turn it on | Worker writes immediately; sanity gate protects; removals reversible | ✓ |

---

## Claude's Discretion

- Failure alerts & freshness UI: the user said to go with Claude's lean and save it for later review (status endpoint, per-request timing logs, Render crash emails, stale warning at 2× cadence).
- CI gates & deploy trigger: the user said to go with Claude's lean and save it for later review (ruff + pytest w/ Postgres + web checks as hard gates, mypy report-only, Render deploys after CI passes).
- Course-row creation mechanism for auto-added courses, window config format, runbook location.

## Deferred Ideas

- Custom consecutive-failure alerting; grade import for auto-added courses; graduate coverage; email seat alerts; mypy hard gate.
