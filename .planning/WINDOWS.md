---
schema_version: 1
open_count: 9
waived_count: 0
fixed_count: 0
total_count: 9
last_updated: 2026-09-24T18:40:36.196Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 03.5 | unrun-verify | tests/api/test_rankings_api.py |  | API suite hangs entering Starlette TestClient under current Python 3.14 environment | open |  | 2026-09-20T17:37:06.936Z |  |
| 2 | 03.5 | deviation | src/easy_a/rankings/service.py |  | Added optional as_of parameter for deterministic seat parity | open |  | 2026-09-20T17:37:06.942Z |  |
| 3 | 03.5 | unrun-verify | tests/refresh/test_postgres_coverage.py |  | PostgreSQL integration verification not run because EASY_A_TEST_POSTGRES_URL is unset | open |  | 2026-09-20T18:06:21.972Z |  |
| 4 | 03.5 | unrun-verify | scripts/check_data_quality.py |  | Quality CLI blocked before database access by pre-existing rankings cache import cycle | open |  | 2026-09-20T18:06:22.143Z |  |
| 5 | 03.5 | deviation | src/easy_a/refresh/coverage.py |  | Filtered the HTML ingestion payload because ingest_schedule_html reparses its input | open |  | 2026-09-20T18:06:22.328Z |  |
| 6 | 03.5 | deviation | tests/refresh/test_targets.py |  | Updated legacy cross-course rejection expectation for D-10 exact-course filtering | open |  | 2026-09-20T18:06:22.514Z |  |
| 7 | 03.5 | unmet-truth | scripts/benchmark_rankings_search.py |  | Rankings-search p95 ~2.40s at 3782-section synthetic scale exceeds the ~1.5s target (REQ-PERF-01 acceptance criterion 2). Accepted deviation: deferred to a post-pilot tuning pass (index/query tuning); pilot scale ~132 sections not user-facing-blocked. Measured 2026-09-20. | open |  | 2026-09-20T22:57:39.281Z |  |
| 8 | 08 | unrun-verify | web/src/components/RankingTable.tsx |  | 08-03 Task 2 manual desktop/mobile browser inspection of course, course/effective_n=0, subject and global rows not run — no browser/Playwright available in this environment; the 8 RankingEvidence.test.tsx component tests render both layouts (jsdom) and assert the exact same strings | open |  | 2026-09-24T18:26:16.640Z |  |
| 9 | 08 | lint-warning | tests/api/test_verify_rankings_pages.py |  | Repo-wide mypy (src migrations scripts tests) grew from the 2026-09-23 planning baseline of 30/9 files to 36/11 files after 08-01/08-02: tests/api/test_verify_rankings_pages.py (5 errors: missing return type annotation, 2x untyped-call, unused type:ignore, int() overload) and tests/refresh/test_inventory_tampa_grades.py (1 error: re-export of scripts.inventory_tampa_grades.os). Both are test files added by 08-01/08-02, outside 08-04's declared file scope (08-VERIFICATION-REPORT.md/08-D21-EXCEPTIONS.md/08-VALIDATION.md only). The three production gate scripts (verify_rankings_pages.py, inventory_tampa_grades.py, validate_tampa_ingest.py) remain mypy-clean. Recorded honestly in 08-VERIFICATION-REPORT.md rather than silently repeating the stale baseline (D-06/D-07). | open |  | 2026-09-24T18:40:36.196Z |  |

````json
[
  {
    "id": 1,
    "kind": "unrun-verify",
    "phase": "03.5",
    "file": "tests/api/test_rankings_api.py",
    "line": null,
    "description": "API suite hangs entering Starlette TestClient under current Python 3.14 environment",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-20T17:37:06.936Z",
    "resolved_at": null,
    "milestone": null
  },
  {
    "id": 2,
    "kind": "deviation",
    "phase": "03.5",
    "file": "src/easy_a/rankings/service.py",
    "line": null,
    "description": "Added optional as_of parameter for deterministic seat parity",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-20T17:37:06.942Z",
    "resolved_at": null,
    "milestone": null
  },
  {
    "id": 3,
    "kind": "unrun-verify",
    "phase": "03.5",
    "file": "tests/refresh/test_postgres_coverage.py",
    "line": null,
    "description": "PostgreSQL integration verification not run because EASY_A_TEST_POSTGRES_URL is unset",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-20T18:06:21.972Z",
    "resolved_at": null,
    "milestone": null
  },
  {
    "id": 4,
    "kind": "unrun-verify",
    "phase": "03.5",
    "file": "scripts/check_data_quality.py",
    "line": null,
    "description": "Quality CLI blocked before database access by pre-existing rankings cache import cycle",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-20T18:06:22.143Z",
    "resolved_at": null,
    "milestone": null
  },
  {
    "id": 5,
    "kind": "deviation",
    "phase": "03.5",
    "file": "src/easy_a/refresh/coverage.py",
    "line": null,
    "description": "Filtered the HTML ingestion payload because ingest_schedule_html reparses its input",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-20T18:06:22.328Z",
    "resolved_at": null,
    "milestone": null
  },
  {
    "id": 6,
    "kind": "deviation",
    "phase": "03.5",
    "file": "tests/refresh/test_targets.py",
    "line": null,
    "description": "Updated legacy cross-course rejection expectation for D-10 exact-course filtering",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-20T18:06:22.514Z",
    "resolved_at": null,
    "milestone": null
  },
  {
    "id": 7,
    "kind": "unmet-truth",
    "phase": "03.5",
    "file": "scripts/benchmark_rankings_search.py",
    "line": null,
    "description": "Rankings-search p95 ~2.40s at 3782-section synthetic scale exceeds the ~1.5s target (REQ-PERF-01 acceptance criterion 2). Accepted deviation: deferred to a post-pilot tuning pass (index/query tuning); pilot scale ~132 sections not user-facing-blocked. Measured 2026-09-20.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-20T22:57:39.281Z",
    "resolved_at": null,
    "milestone": null
  },
  {
    "id": 8,
    "kind": "unrun-verify",
    "phase": "08",
    "file": "web/src/components/RankingTable.tsx",
    "line": null,
    "description": "08-03 Task 2 manual desktop/mobile browser inspection of course, course/effective_n=0, subject and global rows not run — no browser/Playwright available in this environment; the 8 RankingEvidence.test.tsx component tests render both layouts (jsdom) and assert the exact same strings",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-24T18:26:16.640Z",
    "resolved_at": null,
    "milestone": null
  },
  {
    "id": 9,
    "kind": "lint-warning",
    "phase": "08",
    "file": "tests/api/test_verify_rankings_pages.py",
    "line": null,
    "description": "Repo-wide mypy (src migrations scripts tests) grew from the 2026-09-23 planning baseline of 30/9 files to 36/11 files after 08-01/08-02: tests/api/test_verify_rankings_pages.py (5 errors: missing return type annotation, 2x untyped-call, unused type:ignore, int() overload) and tests/refresh/test_inventory_tampa_grades.py (1 error: re-export of scripts.inventory_tampa_grades.os). Both are test files added by 08-01/08-02, outside 08-04's declared file scope (08-VERIFICATION-REPORT.md/08-D21-EXCEPTIONS.md/08-VALIDATION.md only). The three production gate scripts (verify_rankings_pages.py, inventory_tampa_grades.py, validate_tampa_ingest.py) remain mypy-clean. Recorded honestly in 08-VERIFICATION-REPORT.md rather than silently repeating the stale baseline (D-06/D-07).",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-24T18:40:36.196Z",
    "resolved_at": null,
    "milestone": null
  }
]
````
