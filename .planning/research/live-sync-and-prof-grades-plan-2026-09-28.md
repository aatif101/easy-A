# Plan: Live schedule sync first, then professor-level grades

## Context

The grade-feasibility investigation (2026-09-28) found that professor-level grades are blocked by
missing data, not by statistics. Production has **no historical `Section`/`SectionInstructor`
rows**, so `instructor_course` never activates at any threshold. USF's public schedule search still
has those past-term instructors, and they match **8,661 of 8,662** grade rows.

The user wants the more durable fix first: keep seats, instructor names and section existence
**near-live** across all of Easy-A, like Coursicle or ClassRabbit, so nobody has to remember to
re-scrape. Then build professor-level grades on top.

Measured today, and what the design rests on:

- **One request fetches the whole term.** A POST to the existing StaffScheduleSearch endpoint with
  an empty subject and `campus=T` returned all **6,663 Tampa rows / 231 subjects in 9.2 s (7.1 MB)**.
  A full sweep is 1 request, not 212 subject requests.
- **Six days of drift already** (stored 2026-09-20–22 vs. live 2026-09-28, over our 3,783
  sections): 48 Staff→named, 23 named→different name, 13 named→Staff, **92 sections removed at USF
  but still shown in Easy-A**, and 7 new sections in tracked courses that Easy-A doesn't show.
- **The current ingest is append-everything.** `_upsert_sections`
  (`src/easy_a/schedule/ingest.py`) appends a `SectionInstructor` and a `SeatSnapshot` row for
  **every** section on **every** run. At a 10-minute cadence that is about 1.1M rows a day, so it
  has to become change-only.
- **Nothing is hosted yet.** Phase 9 hasn't started, and `docker-compose.yml` is Postgres only.

User decisions: **small always-on container host** (Fly.io / Railway / Render class); **tiered
cadence** (about 5–10 min during registration windows, hourly otherwise); **live sync first, then
professor-level grades**.

---

## Phase A — Live schedule sync (fold into Phase 9 "Hosted Beta")

### A1. Whole-term fetch
- `src/easy_a/schedule/client.py`: add `StaffScheduleClient.search_term(term, campus="T")`, which
  reuses `build_form_data` with an empty `P_SUBJ`. Keep `ScheduleSearchQuery`'s narrow-search
  validation for existing callers, and add a separate explicit full-term path instead of loosening
  it.
- Reuse `parse_schedule_html` and `normalize_schedule_row` unchanged.

### A2. Diff-based sync service (new `src/easy_a/sync/`)
One sweep = fetch → validate → diff against current DB state → apply only the changes → one
transaction.
- **Scope filter:** keep only rows whose `(subject, course_number)` resolves to a tracked course
  (`config/course_targets.toml` via `easy_a.refresh.targets.load_targets` plus `resolve_course_id`)
  and whose campus is `Tampa`. Reuse the existing guards in `refresh_targets`
  (`src/easy_a/refresh/coverage.py`): Tampa-only, and no duplicate CRNs.
- **Sanity gate before any write:** abort the sweep and record a failure if the row count drops
  more than about 10% from the last successful sweep, the parse yields 0 rows, or the header shape
  changes. This keeps a broken or partial USF response from "removing" half the catalog.
- **Section fields:** update in place, as `_update_section` does today, and set `last_seen_at` on
  every sweep, since it already exists on `Section`.
- **Instructor:** append a `SectionInstructor` row **only when the normalized name differs** from
  the current state. Reuse `get_current_instructor_states` (`src/easy_a/common/instructors.py`).
- **Seats:** append a `SeatSnapshot` **only when** capacity, enrollment, seats remaining or waitlist
  changed.
- **New CRNs** in tracked courses: insert through the existing `_section_values` path.
- **Removed CRNs:** set a new nullable `sections.removed_at` when a CRN is absent from a sweep that
  passed the sanity gate. Clear it if the CRN reappears. Search excludes `removed_at IS NOT NULL`.
- **Rankings cache:** if anything changed, run `refresh_section_rankings(session, term=...)`
  (`src/easy_a/rankings/cache.py`). A whole-term rebuild measured 4.77 s. Optimize to per-course
  rebuilds only if sweeps get slow.
- **Observability:** one `IngestRun` row per sweep (the table already exists), with records seen,
  inserted, updated and failed, a change summary, and the error message.

### A3. Freshness semantics
- Seat freshness currently comes from the latest `SeatSnapshot.observed_at` (`snapshot_freshness`
  in `src/easy_a/schedule/freshness.py`, used by `rankings/cache.py` and `rankings/service.py`).
  With change-only snapshots, an unchanged section would look stale.
- Base freshness on **`Section.last_seen_at`** ("verified at"), and keep the seat values from the
  latest snapshot.
- Leave the `EASY_A_SEAT_FRESH_SECONDS` / `EASY_A_SEAT_STALE_SECONDS` thresholds (600 / 1800)
  in place, but align them with the cadence tier.

### A4. Migration
- Alembic: add `sections.removed_at TIMESTAMPTZ NULL`, plus an index on `(term_id, removed_at)` if
  search needs it. This is the only schema change.
- Apply it to hosted Supabase through the normal `MIGRATION_DATABASE_URL` path. It needs explicit
  user go-ahead at execution time.

### A5. Worker process
- New CLI `python -m easy_a.sync --term 202701`: a loop with a cadence schedule, ±20% jitter,
  exponential backoff on HTTP or DB errors, a per-sweep timeout, and a clean exit on SIGTERM.
- **Tiered cadence** comes from config: a list of registration windows (date ranges) → 5–10 min
  inside a window, 60 min outside. Put the windows in `config/` next to `course_targets.toml`.
- Identify politely: keep the existing `DEFAULT_USER_AGENT`. Never run two sweeps at once
  (Postgres advisory lock), so a second worker can't double-poll.

### A6. Hosting (Phase 9 scope)
- One Dockerfile (the uv-based Python image) serving two process types: `api` (FastAPI) and
  `worker` (sync loop). Deploy both to the chosen container host, with Supabase as the DB. Secrets
  go in host env vars (`DATABASE_URL`), never in the repo.
- Add a minimal health signal: the API exposes the last successful sweep time (from `IngestRun`)
  in `GET /api/v1/metadata/coverage`, and the UI shows "Updated N min ago" from it.
- Leave out email seat alerts (backlog 999.1). This worker is the foundation they would build on.

### A7. Planning docs (GSD)
- Update `ROADMAP.md` Phase 9 scope with the live-sync worker, and add Phase 10, "Professor-level
  grades". Update `STATE.md`, and record the decisions (host class, tiered cadence, sequencing) in
  `PROJECT.md` `<decisions>`.
- Save the investigation report to `.planning/research/instructor-grade-feasibility-2026-09-28.md`.

---

## Phase B — Professor-level grades (new Phase 10, after A)

- **B1. Historical backfill:** 5 whole-term fetches (202408, 202501, 202505, 202508, 202601) into
  `Section`/`SectionInstructor`, filtered to courses in the catalog (`resolve_course_id` raises for
  unknown courses, so pre-filter). This populates the join
  `_fetch_instructor_course_grade_observations` already uses; no query change is needed. Expected
  outcome: 3,216 instructor+course pairs, 2,178 with `effective_n ≥ 30`. It is independent of A,
  so it can run early if wanted.
- **B2. Scoring retune** (methodology change, so it needs tests plus a methodology doc per backlog
  999.5):
  - `instructor_course_min_effective_n` 60 → 30.
  - Instructor-level pull toward the course average weighted as about 30 students, instead of
    reusing `grade_prior_strength=60`.
  - Add a single-term flag. 55% of pairs come from one term.
  - Files: `src/easy_a/analytics/scoring.py`, `confidence.py`, and tests.
- **B3. Landmines:**
  - Label or exclude `Laboratory` sections, which are rotating TAs.
  - UI caveat that co-teaching isn't visible in the source.
  - Key any cross-course professor view by name + college, since 242 names appear in more than
    one college.
- **B4. UI:** an instructor breakdown on the course/section view, with "Historically taught by…"
  shown even when the current section says Staff.
- Projected Spring 2027 reach: 751 sections at ≥ 30 today, rising as the live sync resolves Staff.

---

## Verification

- **Unit tests** (pytest, existing SQLite path plus `EASY_A_TEST_POSTGRES_URL`):
  - The diff engine against fixture HTML: an unchanged sweep writes 0 instructor or seat rows; a
    name change writes exactly 1; a removed CRN sets `removed_at`, and a reappearing one clears it.
  - The sanity gate aborts on a short or empty response and leaves the DB untouched.
  - Freshness reads `last_seen_at`.
  - The search API excludes removed sections.
- **Dry-run mode** (`--dry-run`): fetch plus diff against hosted Supabase in a read-only
  transaction. It prints the change summary without writing. Expect roughly the 2026-09-28 numbers
  (about 92 removals, 84 instructor changes, 7 new).
- **Live soak:** run the worker locally for a few hours against Supabase and check that
  `ingest_runs` rows accumulate, that `section_instructors` and `seat_snapshots` grow only on
  change, that each sweep takes under 30 s end to end, and that search p95 stays under 1.5 s
  (`scripts/benchmark_rankings_search.py`).
- **Hosted:** deploy the worker and API. Confirm "Updated N min ago" advances in the UI, and that
  a Staff→named change on USF shows up within one cadence interval.
- **Phase B:** re-run the scratch analysis against the DB after the backfill. Expect the pair
  histogram to match the report (1,329 / 2,178 / 2,829 at ≥ 60 / 30 / 15), and `section_rankings`
  to show about 751 `instructor_course` rows once B2 lands.
