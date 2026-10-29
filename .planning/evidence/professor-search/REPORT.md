# Professor search relevance and section navigation

Observed 2026-10-29. Branch `codex/professor-search`, based on fetched `origin/main`
`131ec209ae6030dabc8e635e148d2a12654074c6`.

## Behavior

- Discovery orders full normalized name matches, complete name words, then word prefixes.
  Within each group, current assignments precede historical-only assignments, followed by
  name and course tie-breakers. Ordering happens before pagination. Matching and attribution
  eligibility are unchanged; names are never expanded or combined across courses.
- Each current instructor result links to only that instructor's sections within the exact
  stored course id. The selected name and course survive copied URLs, reload and browser Back.
  A visible link clears the selection. An assignment that disappears yields an explicit empty
  state rather than silently showing another instructor.
- The existing rankings search accepts additive `course_id` and `instructor` parameters.
  Complete names are compared case-insensitively, trimming outer whitespace, without alias or
  punctuation expansion. Selection runs against cached rankings before count and pagination;
  removed sections and unavailable assignments are excluded. Existing filters still apply.
- Grade scoring, history aggregation, provenance, dependencies and schema are unchanged.
  Autocomplete, fuzzy matching and result-card grade summaries are deferred.

## Validation

- Python 3.12.10, locked dependencies: `pytest tests/api tests/rankings tests/analytics
  --basetemp .cache/professor-search/pytest-run2 -q --tb=short`: **367 passed**. Tests include
  relevance ordering across pages, exact course/name isolation, unavailable/removed assignments,
  literal SQL/wildcard inputs, input bounds, and compatibility with the open-seats filter.
- The existing discovery read-count test still verifies **four SELECTs**. A new filtered-ranking
  test verifies **two reads** with no instructor-history or grade-table scan, and no seat scan in
  the count query. The frontend selection test verifies one ranking request for a one-page course.
- Frontend: **134 tests passed**, ESLint, TypeScript and production build passed. Tests cover
  encoded names, malformed selections, direct links, clearing the selection, browser Back and
  the explicit synthetic demo adapter. New selections reset the page using the full route key.
- Ruff passed; targeted mypy passed for both changed endpoint modules and their tests.
- Browser verification used explicit synthetic demo mode on localhost. Searched Alvarez,
  selected Jordan Alvarez's ENC 1101 sections (only CRN 14022), cleared the selection (CRNs
  14022 and 14023), and used Back to restore the selection. Desktop capture: 1280x720;
  mobile: 320x844. Mobile document width equaled viewport width (320 px); no browser warning
  or error logs. Screenshots: [desktop](desktop.png), [mobile](mobile.png).
- Initial broader tests hit the existing Windows pytest temp-directory permission problem;
  rerunning with the explicit workspace-local `--basetemp` above resolved all setup errors.
  Starlette emits its existing httpx TestClient deprecation warning.

## Latency comparison

Reproduce with `uv run --python 3.12 --locked python
.planning/evidence/professor-search/benchmark.py`. The baseline endpoint is loaded from the
pinned main commit above. All data is generated in an in-memory SQLite database: 1,400 courses,
3,782 current sections, 8,600 historical sections, and one synthetic assignment per section.
Each query has three warmups and 30 measured samples, alternating before/after order with
response caching bypassed. The final run was separate from frontend/backend test execution.
Raw results: [performance.json](performance.json).

| Synthetic query | Before p50 | After p50 | Before p95 | After p95 |
|---|---:|---:|---:|---:|
| smith | 304.26 ms | 306.90 ms | 357.23 ms | 352.16 ms |
| j smith | 322.98 ms | 320.55 ms | 391.05 ms | 386.50 ms |
| smi | 256.43 ms | 264.91 ms | 322.15 ms | 341.81 ms |
| no such name | 226.92 ms | 232.39 ms | 274.72 ms | 257.25 ms |

Discovery costs remain close in this sample; p95 changes range from -17.47 to +19.66 ms.
This measures direct endpoint execution on local Python/SQLite. It excludes HTTP, network,
hosted PostgreSQL, cache behavior and rendering; it does **not** establish hosted p95 or promise
the 1.5 s production budget. The new section filter is covered by request/query-count checks,
not by this discovery timing benchmark. No hosted DB or USF request was needed for this change.

## Security review

Scope: the changed public GET handlers and browser query-string route. No actionable security
findings in this diff.

- Injection/tampering: `src/easy_a/api/routes/rankings.py:102` builds parameterized SQLAlchemy
  predicates, with tests for SQL metacharacters and wildcard literals. No user-controlled SQL,
  file paths, network destinations, writes, or new privileges.
- Identity/information disclosure: `rankings.py:78` requires a course for instructor selection;
  `rankings.py:98` scopes it to the stored course and active sections. The existing public ranking
  payload is returned. Unavailable assignments are excluded. No cross-course person identity
  or grade pooling is introduced.
- Denial of service: `rankings.py:58` bounds the course id and instructor length; existing bounded
  pagination remains in place. Selection uses narrow cached columns and stays at two reads.
  Discovery retains its existing query bounds and four reads, with no fuzzy scans or new calls.
- XSS/navigation: `web/src/lib/route.ts:30` encodes the listed name into a relative URL; React
  escapes displayed names. Tests round-trip punctuation, ampersands and Unicode.
- Spoofing, repudiation and privilege elevation: these public read-only changes introduce no
  accounts, credentials, mutation endpoints, or security-boundary changes.

Live hosted performance and deployments are outside this verification. The user's pre-existing
lockfile edit and pytest scratch directory are preserved and excluded from the feature commit.
