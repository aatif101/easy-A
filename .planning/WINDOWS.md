---
schema_version: 1
open_count: 2
waived_count: 0
fixed_count: 0
total_count: 2
last_updated: 2026-09-20T17:37:06.942Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 03.5 | unrun-verify | tests/api/test_rankings_api.py |  | API suite hangs entering Starlette TestClient under current Python 3.14 environment | open |  | 2026-09-20T17:37:06.936Z |  |
| 2 | 03.5 | deviation | src/easy_a/rankings/service.py |  | Added optional as_of parameter for deterministic seat parity | open |  | 2026-09-20T17:37:06.942Z |  |

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
  }
]
````
