# Hosted Beta Operations Runbook

Use this runbook to operate the hosted Easy-A beta: check its health, refresh data, recover from a failed sweep, pause the worker, measure search latency and handle the calendar events that need a human.

The beta runs as three Render services created from `render.yaml` (one Docker image is used for the API and the worker):

| Service | Type | What it does |
|---|---|---|
| `easy-a-api` | web (Docker) | FastAPI read API, health check `/health`, sync status at `/api/v1/metadata/sync-status` |
| `easy-a-worker` | worker (Docker) | `python -m easy_a.sync --term 202701`: one whole-term USF request per sweep on the tiered cadence |
| `easy-a-web` | static site | The React front end, built with `cd web && npm ci && npm run build` |

All three are in region ohio. Public URLs follow the pattern `https://<service-name>.onrender.com` (Render adds a random suffix if the name is taken). Expected cost is about $14/month (two `starter` services; the static site is free). The database is hosted Supabase, reached through the transaction pooler (port 6543).

## Preconditions and standing rules

- `DATABASE_URL` (Supabase transaction pooler) is set on `easy-a-api` and `easy-a-worker`. It was entered per service when the Blueprint was created: the dashboard environment group `easy-a-shared` exists and holds it, but `render blueprints validate` rejects `fromGroup`, so `render.yaml` does not use the group. If you rotate the password, update the group and both services.
- **Migrations are manual.** Apply them from a workstation with `MIGRATION_DATABASE_URL` pointing at the Supabase **session** pooler, and do it **before** merging code that needs them. The worker and the API refuse to start against a schema that is not current (worker exit code 4, "startup check failed"). Never add `MIGRATION_DATABASE_URL` to Render and never run migrations from the image at start-up.
- **Do not run `scripts/refresh_all_tampa.py`, `scripts/refresh_seats.py` or `scripts/refresh_course_coverage.py` for 202701 once the worker is live.** They append every row and issue many requests, which breaks the request policy and bloats `seat_snapshots`. The worker replaces them for this term.
- **Request policy (PROJECT.md D-22):** one whole-term USF request per sweep, at most one sweep in flight, and floors of 5 minutes inside a registration window and 60 minutes outside. No flag bypasses the floor. A dry run is a real USF request, so leave one tier interval after it before starting or restarting the worker.
- `[skip render]` in a commit message skips the Render deploy for that commit. `buildFilter` paths already keep docs-only and `.planning/` commits from restarting the worker.

## 1. Daily health check

```bash
curl -fsS https://easy-a-api.onrender.com/health
curl -fsS "https://easy-a-api.onrender.com/api/v1/metadata/sync-status?term=202701"
```

Replace the host with the real `easy-a-api` URL if Render added a suffix. Fields of the sync-status response:

| Field | Meaning |
|---|---|
| `last_success_at` | Finish time (UTC) of the latest succeeded sweep; null if none exists |
| `last_run_at`, `last_status` | Start time and outcome (`succeeded` or `failed`) of the latest sweep of any status |
| `last_error_kind` | Coarse kind of the latest failure (table below); null unless it failed |
| `last_records_failed` | Rows of the latest sweep that could not be applied (for example auto-add failures) |
| `failures_last_24h` | Count of failed sweeps in the last 24 hours |
| `in_registration_window`, `cadence_seconds` | Whether a D-02 window is open and the current sweep interval |
| `stale_after_seconds`, `is_stale` | Data is stale after twice the cadence without a success |
| `as_of` | Time the response was computed |

Healthy means `last_status` is `succeeded`, `is_stale` is `false` and `failures_last_24h` is 0 or a short isolated run. Error kinds: `usf_http`, `usf_timeout`, `usf_response`, `parse`, `scope`, `gate`, `database`, `schema`, `unexpected` (the raw error text is never exposed). Section 4 has the playbook for each.

## 2. Refresh data now

```bash
uv run python -m easy_a.sync --term 202701 --once
```

Run from a workstation with `DATABASE_URL` set, or in a Render shell of `easy-a-worker`. It runs one sweep and exits. Exit codes: `0` succeeded, `1` failed, `2` another sweep holds the lock, `3` refused by the cadence floor (the message prints the earliest allowed time), `4` startup check failed. Exit 3 is normal right after a sweep; wait and retry. There is no override.

## 3. Dry run

```bash
uv run python -m easy_a.sync --term 202701 --dry-run
```

A dry run makes the real USF request, computes what a sweep would do inside a read-only transaction and writes nothing. It prints one JSON line. Read the `scope` object first (the D-03 scope report): it shows `total_rows` USF returned, `distinct_crns`, the rows excluded as `non_tampa_rows`, `graduate_rows` and `unparseable_number_rows`, the `in_scope_rows` kept, and the number of `subjects` and `course_keys` in scope. Then check `inserted`, `updated`, `removed`, `restored`, `instructor_changes`, `seat_changes`, `would_add` (courses a real sweep would auto-add) and `gate_reasons` (why the sanity gate would refuse).

A dry run is refused with exit 3 when it falls inside the floor of the last **recorded** sweep. A dry run records no `IngestRun`, so repeated `--dry-run` calls are **not rate-limited** by the tool, and neither the worker nor `/sync-status` ever sees them. Every one is a real USF request, so do not repeat them faster than the tier interval by hand.

## 4. Recover from a failed sweep

Find the kind in `last_error_kind` (section 1) or in the worker log line `sweep_failed` (`error_kind`, `error_detail`). The worker keeps running and backs off; it never starts inside the tier floor.

| Kind | Meaning | Action |
|---|---|---|
| `usf_http`, `usf_timeout` | USF returned an error or was slow or unreachable | Wait: the worker backs off and retries at the next allowed time. If it persists for several hours, check the USF site by hand |
| `usf_response`, `parse` | USF changed its page or the response is not the expected whole-term table | Suspend the worker (section 5) and investigate. Do not loosen anything to get past it; the parser is fail-closed on purpose |
| `scope` | The response could not be scoped safely | Treat like `parse`: suspend and investigate |
| `gate` | The sanity gate refused (empty response, header change, too many sections missing, row floor, subject drop) | Run `--dry-run` and read `gate_reasons`. If the change is real, run `uv run python -m easy_a.sync --term 202701 --once --max-missing-fraction X` (default 0.10) **only** with a written justification in the Run Log below |
| `database` | A database error (connectivity, pooler, timeout) | Check Supabase status and the connection limits, then wait for the next sweep |
| `schema` | The database schema is behind the code | Apply the pending migration from a workstation (see Standing rules), then restart the worker |
| `unexpected` | Anything else | Read the worker log, suspend if it repeats, and open an issue with the sanitized log line |

## 5. Pause and resume the worker

Render Dashboard, `easy-a-worker`, **Suspend** to pause and **Resume** to restart. The worker honours the persisted last sweep time on restart, so resuming never sweeps inside the floor. While paused, the student site shows the stale warning once data is older than twice the cadence; that is expected. Leave one tier interval after any manual run (a dry run in particular) before resuming.

## 6. Un-mark a wrongly removed section

Sections USF omits from a sweep are marked with `removed_at` and disappear from search. A full sweep restores any section USF lists again automatically. To restore one immediately (no USF request is made):

```bash
uv run python -m easy_a.sync --term 202701 --restore-crn 12345 --restore-crn 23456
```

Exit 0 means at least one section was restored and the ranking cache was rebuilt; exit 1 means nothing was restorable (the log line lists `not_found` and `not_removed`). If USF still omits the section, the next sweep marks it removed again, which is correct.

## 7. Measure search latency (p95)

From exported `easy_a.request` log lines (Render Dashboard, `easy-a-api`, Logs, download or copy), compute p95 with the standard library:

```bash
python3 - <<'PY' < api-logs.txt
import json, sys, math
values = []
for line in sys.stdin:
    start = line.find("{")
    if start < 0:
        continue
    try:
        record = json.loads(line[start:])
    except ValueError:
        continue
    if record.get("event") == "request" and record.get("route") == "/api/v1/rankings/search":
        values.append(record["duration_ms"])
values.sort()
if values:
    print(f"n={len(values)} p95_ms={values[math.ceil(0.95 * len(values)) - 1]}")
else:
    print("no matching lines")
PY
```

Or measure the deployed API directly (HTTPS only, no database access, no credentials):

```bash
uv run python scripts/benchmark_rankings_search.py --remote-url https://easy-a-api.onrender.com --iterations 50
```

The MVP-1 target is p95 under about 1.5 s. The first request after idle can be slow, so read the whole distribution.

## 8. Alerts

The only alerts are Render's built-in email notifications for failed deploys and service failures (D-09). They do **not** fire when the worker is alive but every sweep fails. That gap is why the daily check in section 1 exists. There is no paging and no external monitor.

## 9. Auto-added courses and D-21 accounting (D-05)

The worker can add an in-scope course that is not in `config/course_targets.toml` through a paced catalog lookup. The accounting decision (D-05):

1. `config/course_targets.toml` stays the frozen configured list and the worker never writes it (the container filesystem is ephemeral).
2. An auto-added course is derived, not stored: it has at least one active 202701 section and is not a configured target. There is no schema marker.
3. `/api/v1/metadata/coverage` keeps meaning configured targets.
4. `scripts/validate_tampa_ingest.py` lists auto-added courses as an allowed category (an `INFO auto-added (D-05)` line) and reconciles active sections against configured targets plus auto-added sections. An untargeted graduate or non-Tampa course still fails.
5. The D-21 inventory shows their sections as listed exceptions with their honest subject or global fallback label, never as evidence-backed history (D-20, D-21). `08-D21-EXCEPTIONS.md` remains the dated 2026-09-24 record.

## 10. Registration windows

The cadence comes from `config/registration_windows.toml` (America/New_York local days): Nov 2 to Nov 30, 2026 (priority registration), Jan 7, 2027 (state employees) and Jan 11 to Jan 15, 2027 (drop/add). Sweeps run about every 5 minutes inside a window and hourly otherwise. To change dates, edit the file and deploy; no code change is needed.

- USF marks these dates as subject to change. **Re-check the registrar pages named in the file before 2026-11-02.**
- Open question 3: whether to make Jan 7 to Jan 15 one contiguous window. D-02 locks them as separate; extending it is a one-line edit if the owner decides so.
- Open question 8: about 10,080 whole-term requests are expected over the D-02 windows. Confirm the owner accepts that volume, and check `content_encoding` and `bytes` in the first sweep's log line.

## 11. Term rollover

The worker is per term. Summer and Fall 2027 registration opens Mar 29, 2027. Before then: add a new window file for the new term, change `--term` in `render.yaml` (`dockerCommand` on `easy-a-worker`), update the health-check URLs, and re-validate with `render blueprints validate render.yaml -o text`. The worker refuses to start when the window file's term differs from `--term`.

## 12. Cancelled sections

Sections USF lists as cancelled (`secondary_status` `U` or `C`, about 359 undergraduate rows at the last check) are currently shown like any other section, because they are present in the sweep and are not "removed". Whether to hide or label them is a pending owner decision (open question 2); the meaning of status `R` is also unconfirmed.

## 13. Deploy ordering

1. Merge and push only after CI is green: Render deploys on `checksPass`, and the workflow runs on every push with no path filters.
2. If the change needs a migration, apply it manually first (Standing rules), then merge.
3. A deploy briefly overlaps the old and new worker for up to about 90 seconds (`maxShutdownDelaySeconds`). The database advisory lock keeps it to one sweep in flight.
4. After the first restart, confirm the old worker's log ends with the `worker_stopped` line; then confirm `/health` and section 1.
5. After the first Blueprint create, fill `EASY_A_ALLOWED_FRONTEND_ORIGINS` (exact static-site origin: scheme and host, no trailing slash) and `VITE_API_BASE_URL`, then redeploy the static site (`VITE_*` is baked in at build time).

## Run Log

| Date (UTC) | Operator | Action | Command / setting | Result | Justification |
|---|---|---|---|---|---|
| | | | | | |
