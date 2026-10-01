# Phase 10: Professor-level grades - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-30
**Phase:** 10-professor-level-grades
**Areas discussed:** D-24 scoring retune, Backfill execution, Instructor breakdown UI, Landmines

---

## D-24 scoring retune

| Question | Options | Selected |
|---|---|---|
| Approve D-24? | Approve full retune / Display-only first / Approve partially | Approve full retune |
| Single-term flag behavior | Label only / Label + stronger shrinkage / Require 2+ terms | Label only |
| Constants in code | New named config fields / Reuse grade_prior_strength / You decide | New named config fields |
| Rollout gate | Before/after diff report / Just ship with tests / Feature flag | Before/after diff report |

## Backfill execution

| Question | Options | Selected |
|---|---|---|
| How to run | One-off CLI script / Worker job / Reuse sync code | One-off CLI script |
| Rows to write | Only grade-matched sections / All catalog sections / Everything pulled | Only grade-matched sections |
| Safety | Dry-run + idempotent + tagged / Supabase branch rehearsal / You decide | Dry-run + idempotent + tagged |
| Staff rows | Store as Staff, never match / Skip | Store as Staff, never match |

## Instructor breakdown UI

| Question | Options | Selected |
|---|---|---|
| Location | Inside RankingDetails / Separate course page / Inline in rows | Inside RankingDetails |
| Which instructors | All with enough history, current first / Current only / Everyone no cutoff | All with enough history, current first |
| Staff sections | Display only / Blend expected score | Display only |
| Row contents | A% + n + terms + shrunk score / Raw only / Full distribution bar | A% + n + terms + shrunk score |

## Landmines

| Question | Options | Selected |
|---|---|---|
| Labs | Exclude from stats, label in UI / Include but label / Exclude silently | Exclude from stats, label in UI |
| Name collisions | Within-course by name; name+college elsewhere / Always name+college | Within-course by name; name+college elsewhere |
| Caveats | InfoTip + per-row chips / Persistent banner / Methodology page only | InfoTip + per-row chips |

## Claude's Discretion

Min-n collapse cutoff, API shape, config field name, copy, CLI flags, backfill-before-scoring ordering.

## Deferred Ideas

Cross-course professor page; Staff-section blended score (rejected); full distribution bars; Phase 9 carry-overs.
