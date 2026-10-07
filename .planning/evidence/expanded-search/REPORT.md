# Expanded search — local implementation and verification

Observed October 7, 2026. Work is prepared for a pull request on `codex/expanded-search` in
`C:/Users/kanis/OneDrive/Documents/Projects/easy-A-expanded-search`, directly descended from
fetched `origin/main` `b4daecd608b415490cbb9382be5f95a71512ef8a` (includes merged header PR #43).
The user explicitly requested a PR after local implementation. No merge, deployment,
source crawl, RMP request or live data mutation occurred.

## Changed files and behavior

- `src/easy_a/search.py`: central production query interpretation; literal case-insensitive
  title/name token matching; punctuation and spacing normalization. Numeral title tokens
  1–4 match their Roman counterparts I–IV, with boundaries preventing I from matching II/III.
- `src/easy_a/api/routes/discovery.py` and `src/easy_a/api/app.py`: additive database-only
  discovery and grade-record endpoints. Existing rankings endpoints and analytics are unchanged.
- `web/src/types/search.ts`, `web/src/api/rankings.ts`, `web/src/App.tsx`,
  `web/src/pages/ResultsPage.tsx`, `web/src/pages/DiscoveryPage.tsx`: submit-based search,
  separately labeled course/instructor results, server pagination, historical grade details,
  loading/empty/error/retry, cancellation and ignored stale responses. CRN/course/subject routes
  retain existing comparisons, sorting, filters, copy controls and evidence labels. A subject-shaped
  professor query such as a three-letter surname can show instructor matches. Catalog-only
  courses can open historical records without pretending there is a current section.
- `web/src/components/SearchBox.tsx`, `web/src/components/Status.tsx`,
  `web/src/pages/HomePage.tsx`: supported-input hints and context-specific failure messages.
- `tests/api/test_discovery.py`, `web/src/pages/DiscoveryPage.test.tsx`,
  `web/src/api/rankings.test.ts`, `web/src/App.test.tsx`: search, identity, history, bounds,
  provenance, read-only query counts, navigation, keyboard selection and cancellation tests.
- `README.md`, `.planning/STATE.md`: API semantics, normalization, identity limits and fresh state.
  A continuation pointer is also recorded in the original checkout's STATE.md.

No production dependency, schema migration, scoring, confidence constant, rank ordering,
grade ingestion or attribution implementation changed. Existing RMP links were not removed;
the fetched baseline had none in `web/src`, and pending RMP PR work remains separate.

## API contract

`GET /api/v1/search?term=202701&q=...&limit=20&offset=0` returns canonical query kind/key,
courses with subject/number/official stored title/catalog edition/ID/current section count,
instructor-course records with current/historical assignment counts and observation date,
independent totals, pagination and a database-read timestamp. Four SELECT statements,
no N+1 hydration; default 20 per category, maximum 50, offset 0–10,000, query maximum 200 characters.

`GET /api/v1/search/history?term=202701&course_id=...&name=...&limit=20&offset=0` returns exact
covered terms, stored grade buckets, observed A–F denominator, A share and bounded term/CRN/source
records with source hashes/import dates. Omit name for own-course records. Small samples retain
insufficient labels using existing constants (30 instructor, 60 course); no letter grades means
no A share; absent history stays unavailable. There is no professor-wide easiness score.

## Identity and source limitations

The database has no college identity field. Each listed name stays separate within a course
record/catalog edition; names across courses are not merged or declared to be the same person.
Initials stay initials. Search uses one usable name at the latest section observation. Staff,
blank, TBA/TBD/ARR/unknown/unavailable/N/A/none and ambiguous latest assignments are excluded.
Historical sections with conflicting name observations are excluded from named results and
history; labs are excluded from instructor grade history. This conservative discovery view
declines unsafe attribution without changing existing historical analytics or caches.

Missing and suppressed exports cannot be reconstructed. The existing stored schema has no
suppression marker, so this work does not infer suppression from a zero or invent a distribution.
Subject/global prior-only scores are never used to fill this own-course grade-record view.
Frontend-only mock mode remains explicitly synthetic and declines detailed raw records it lacks.

## Fresh checks

- Python 3.12.13, locked dependencies: **42 new search tests pass**; focused API/rankings/history
  regression selection **124 passed**, one existing FastAPI TestClient deprecation warning
  (`focused-backend.log`).
- Full backend: **1075 passed, 10 failed, 4 skipped, 1 xfailed** (`backend-full.log`). All ten
  failures reproduced on an untouched `origin/main` archive under the same environment
  (`baseline-failures.log`): five Windows `os.fchmod` backfill tests, four parser negative-control
  tests and one worker SIGTERM test. PostgreSQL-dependent tests skip without a test database.
- `ruff check .`: passed. Mypy on both new backend modules: passed. Whole `mypy src` has four
  existing Windows platform errors in `schedule/backfill_cli.py` and `sync/cli.py` (`fchmod`,
  `resource.getrusage`/`RUSAGE_SELF`, consequent Any return). Those files were not changed.
- Frontend: **46 passed / 4 files**; `npm run lint`, `npm run typecheck`, `npm run build` passed.
  `npm ci` reported 12 vulnerabilities in the baseline dependency graph; no dependency upgrades
  or lockfile edits were made. `git diff --check` passed.
- The original `web/package-lock.json` retains SHA256
  `161F2B69CB1EC8CF0B72CC8BA54903528842A802C011CD6F499F80FE5D377779`;
  the original `.pytest-tmp-codex-20260914a/` was preserved.

## Browser and performance evidence

Inspected the running Vite UI over the local fixture API at **1440×1000** and **320×844**.
The header explicitly says SYNTHETIC PREVIEW. Verified mixed title/instructor matches,
ambiguous course-number selection, navigation into the original comparison table and its
filters/sort/copy controls, historical-only instructor details, keyboard Enter activation,
long titles/names wrapping, source hashes and covered terms. Document width equals 320px
at mobile width. Screenshots: `desktop.png`, `mobile.png`.

One local SQLite preview history request returned 500; the visible retry recovered and ten
subsequent identical HTTP requests returned 200. No definitive cause was established; this is
recorded rather than counted as an always-successful UI check. Final inspected browser console
had only Vite/React development messages and no page errors. Tests also verify retry/error states.

`performance.json`: **local synthetic in-process FastAPI TestClient + SQLite**, 1402 generated
courses, 3782 generated current sections and 8600 generated historical sections/grade rows,
in addition to the small focused fixture. Five warmups and 50 measured calls per query:

| Query | p95 |
|---|---:|
| 1101 | 170.68 ms |
| calculus 1 | 216.74 ms |
| Program Design | 225.12 ms |
| Synthetic Instructor 12 | 219.65 ms |

These are not hosted, concurrent-user, browser-end-to-end or PostgreSQL measurements, and are
not claimed as production acceptance of the approximately 1.5-second target. Saved Supabase
credentials failed authentication; Docker's PostgreSQL daemon was not running. Hosted expanded
search, real PostgreSQL execution and a live-data UI check remain unavailable. No attempt was
made to deploy the feature to obtain those measurements.

Before PR publication, reran the focused backend selection (124 passed), frontend suite
(46 passed), Ruff, targeted mypy, frontend lint/typecheck/build and diff checks successfully.

Next: owner review of the PR; working read-only database access is needed for hosted/PostgreSQL
verification. Merge and deployment are not authorized. No new milestone was created.
