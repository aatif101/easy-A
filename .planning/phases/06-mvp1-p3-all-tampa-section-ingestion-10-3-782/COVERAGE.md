# Phase 6 — External API Coverage (advisory)

**Produced:** 2026-09-21 (plan time)
**Checkpoint:** API Coverage (ai-integration) — advisory, non-blocking

## Declaration

**No rich external API integration.** This phase issues only bounded, deterministic HTTP requests
to two existing USF public endpoints already wired into the codebase — it does not integrate a
verb-rich API, so there is no capability surface to enumerate. The two endpoints are:

| Endpoint (existing) | Method | Verb surface | Disposition | Reason |
|---------------------|--------|--------------|-------------|--------|
| `cloud.usf.edu/academic-programs/details/prefix/{subject}/code/{number}` (catalog course detail) | GET | Single course-detail fetch, one course per page | INTEGRATE (reused unchanged) | Only path to create the `Course` rows `resolve_course_id` requires; no bulk verb exists |
| `usfweb.usf.edu/DSS/StaffScheduleSearch/StaffSearch/Results` (staff schedule search) | POST (form) | Single narrow term+campus+subject/course search | INTEGRATE (reused unchanged) | Only path to fetch Tampa sections; queried per exact course |

Everything else USF might expose (registration, program listings, other campuses, other terms) is
**OPT-OUT** by scope: D-08/D-09 forbid scraping/crawling; this phase widens only the *volume* of
the same two bounded requests, never their surface. No new client, no new endpoint, no new verb is
added. `src/easy_a/catalog/client.py::fetch_catalog_html` and
`src/easy_a/schedule/client.py::StaffScheduleClient.search` are reused with unchanged signatures.

## Volume note

Scaling from 10 → ~1,402 courses turns these two bounded requests into ~1,402 catalog GETs plus up
to ~1,402 schedule POSTs. Volume — not surface — is the new risk, mitigated by per-subject batching
and deliberate pacing (see the phase threat model and `06-02-PLAN.md`).
