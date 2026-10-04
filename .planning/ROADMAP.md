# Roadmap: Easy-A

## Milestones

- ✅ **v1.0 MVP 1** — Phases 1-10 (shipped 2026-10-04): full Tampa coverage, historical grades, search p95 < ~1.5 s, hosted beta, professor-level grades. Archive: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md), requirements: [milestones/v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md), audit: [milestones/v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md) (status `tech_debt`).
- 📋 **Next milestone** — not yet defined. Start with `/gsd-new-milestone`.

## Phases

<details>
<summary>✅ v1.0 MVP 1 (Phases 1-10) — SHIPPED 2026-10-04</summary>

- [x] Sprint 5 / Phase 1 / Phase 2 — complete and merged (dated results in `.planning/ARCHIVE.md`)
- [x] Phase 3: Historical grade coverage — folded into MVP 1 (Phases 4-5)
- [x] Phase 3.5: Ranking search performance — perf goal met via Phase 7
- [x] Phase 4: MVP1-P1 — Grade→course attribution fix
- [x] Phase 5: MVP1-P2 — Grade data sourcing + import to Supabase
- [x] Phase 6: MVP1-P3 — All-Tampa section ingestion (10 → ~3,782)
- [x] Phase 7: MVP1-P4 — Full-scale cache build + search performance
- [x] Phase 8: MVP1-P5 — End-to-end MVP-1 verification
- [x] Phase 9: Hosted beta — deployment, CI, observability (11 plans; open gap: sweep duration 37-51 s vs 30 s)
- [x] Phase 10: Professor-level grades (11/11 plans, completed 2026-10-04)

Phase detail, goals and success criteria: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md).

</details>

---

## Backlog — candidate later phases

Not scheduled. Not committed. None is required for the hosted beta, and none should be pulled
into the current execution sequence.

### Phase 999.1: Seat alerts and notifications (candidate later phase)

**Not current scope.** Appropriate only after the hosted beta is stable. Do not add subscriber,
watch, outbox or email-provider work to the current sequence.

Design considerations preserved as **future / optional only**: a durable worker independent of
any browser session, polling shared across subscribers, a persisted outbox with idempotency and
bounded retries, verified email ownership before any send, and honest language distinguishing
provider acceptance from inbox receipt.

### Phase 999.2: Verified RMP profile links (candidate later phase)

**Not current scope.** Deferred until after hosted beta and core data stability. Not a blocker.
Whenever picked up: no scraping, no bulk crawler, and no imported ratings, review counts, review
text, tags or summaries — a verified link only.

### Phase 999.3: Deeper professor-specific coverage — promoted to Phase 10 (2026-09-28)

The 2026-09-28 investigation showed named-instructor coverage is recoverable from the public
schedule (8,661 / 8,662 grade rows matched). See Phase 10.

### Phase 999.4: Additional UX features (candidate later phase)

Deep links, a methodology page, and expanded accessibility work.

### Phase 999.6 — promoted to MVP1-P4 (no longer backlog)

Full-scale ranking search tuning (p95 < ~1.5s on Supabase, plus the benchmark env-label fix) was
briefly a deferred backlog item. Because MVP 1 targets hosted Supabase at full ~3,782-section
scale, it is now **blocking phase MVP1-P4** in the MVP 1 milestone above.

### Phase 999.5: Methodology review (optional research item)

The current scoring model is the baseline and stays. An evidence-backed review of how it behaves
with little or no grade history is an **optional research item, not active implementation scope**.
Any change would require documented evidence plus matching methodology and test updates. No
rewrite is planned or approved.

---

