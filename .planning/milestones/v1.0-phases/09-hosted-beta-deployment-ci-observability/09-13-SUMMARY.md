---
phase: 09-hosted-beta-deployment-ci-observability
plan: 13
subsystem: infra
tags: [docker, uv, render, blueprint, ci, runbook, deployment]
status: complete

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-01 CI workflow, 09-10 D-05 accounting, 09-11 worker CLI, 09-12 course auto-add"
provides:
  - "Single uv-based Dockerfile: API by default, worker via dockerCommand override"
  - ".dockerignore keeping .env and bulk data out of the build context"
  - "render.yaml Blueprint (easy-a-api, easy-a-worker, easy-a-web), validated with the Render CLI"
  - "CI docker job: builds the image and checks tzdata, worker --help, API import, RSS, non-root, no .env"
  - "tests/test_deploy_config.py static invariants"
  - "docs/runbooks/hosted-beta-operations.md operator runbook and README pointer"
affects: [09-14, 09-15]

actuals:
  tokens: 7000
  tasks: 3
  commits: 2
plan_head_before: 73481af4beea7e3fdac6d7649492de0d5e396b11
plan_head_after: 4d7ea79bf45e434fb33875e22e80586f57bedfab

tech-stack:
  added: []
  patterns:
    - "tzdata from the Debian apt package inside the pinned base image, no PyPI tzdata"
    - "Secrets only via sync:false in render.yaml; tests reject any value line for DATABASE_URL, MIGRATION_DATABASE_URL, VITE_API_BASE_URL and EASY_A_ALLOWED_FRONTEND_ORIGINS"
    - "exec-form sh -c CMD so uvicorn is PID 1 and receives SIGTERM"

key-files:
  created:
    - Dockerfile
    - .dockerignore
    - render.yaml
    - tests/test_deploy_config.py
    - docs/runbooks/hosted-beta-operations.md
  modified:
    - .github/workflows/ci.yml
    - tests/test_ci_workflow.py
    - README.md

key-decisions:
  - "Env-group answer (Open Question 1): the operator replied group-ok, meaning easy-a-shared exists in the Render dashboard with DATABASE_URL. The fromGroup variant still failed `render blueprints validate` ('depends on non-existent group: easy-a-shared', both services), so render.yaml keeps per-service DATABASE_URL with sync: false. The operator fills it once per service (api and worker) at Blueprint creation, copying from the group. The reason is recorded in the render.yaml header comment and the runbook."
  - "tzdata comes from apt; no PyPI dependency added, so no package-legitimacy checkpoint was needed."
  - "Runbook states that repeated --dry-run calls are not rate-limited: a dry run records no IngestRun (verified in sweep.py: success and failure paths skip IngestRun when dry_run), so neither the cadence floor nor /sync-status sees it. Each is a real USF request, so the operator self-limits to the tier interval."

requirements-completed: [REQ-OPS-01]

duration: about 25 min
completed: 2026-09-30
---

# Phase 9 Plan 13: Deployment Config and Operator Runbook Summary

**One uv-based Docker image for API and worker, a Render Blueprint validated by the CLI (per-service `DATABASE_URL`, `sync: false`), a CI `docker` job, and a 13-section hosted-beta operator runbook.**

## Accomplishments

- **Image.** `python:3.12-slim-trixie`, uv 0.12.17 from `ghcr.io/astral-sh/uv`, `uv sync --locked --no-dev`, `WORKDIR /app` with `src`, `config`, `migrations` and `alembic.ini`, apt `tzdata`, non-root uid 10001, exec-form CMD `uvicorn easy_a.api.app:app --host 0.0.0.0 --port ${PORT:-10000} --no-access-log`. No ARG or ENV carries a secret.
- **Blueprint.** Three services in region ohio: api and worker on `starter`, all with `autoDeployTrigger: checksPass` and `buildFilter` paths. The worker runs `python -m easy_a.sync --term 202701` with `maxShutdownDelaySeconds: 90`. The static site builds `web/dist` with `VITE_USE_MOCK_DATA "false"`, `NODE_VERSION "24"` and an SPA rewrite. `render blueprints validate render.yaml -o text` returns `"valid": true`.
- **CI.** New `docker` job builds the image on every push and PR and checks: `ZoneInfo('America/New_York')` loads, `python -m easy_a.sync --help`, `import easy_a.api.app`, an import RSS under 150 MB, `id -u` is not 0, `/app/.env` is absent and `config/registration_windows.toml` exists.
- **Tests.** `tests/test_deploy_config.py` has 16 stdlib text checks. With `tests/test_ci_workflow.py`, 29 pass.
- **Runbook.** Standing rules plus sections 1-13 (daily health, refresh, dry run, recovery per error kind, pause and resume, `--restore-crn`, p95 measurement, alerts, D-05 and D-21 accounting, windows, term rollover, cancelled sections, deploy ordering) and a Run Log. README has a "Hosted beta (Render)" pointer.

## Task Commits

| Task | Commit | Notes |
|---|---|---|
| 1 (tracer) | 3c5843b | Dockerfile, .dockerignore, render.yaml, CI docker job, tests |
| 2 (checkpoint) | none | Operator answered `group-ok`; fromGroup variant failed validation |
| 3 | 4d7ea79 | render.yaml header note, runbook, README pointer |

## Checkpoint Record (Task 2)

Validator output for the repository file (per-service `DATABASE_URL`): `"valid": true`. For the `fromGroup: easy-a-shared` variant on api and worker: `"valid": false` with `env var group linkage depends on non-existent group: easy-a-shared` for both. The operator confirmed the group exists in the dashboard (`group-ok`). Per the plan, the Blueprint switches to `fromGroup` only when the variant validates, so the per-service form stays. The validator apparently sees only Blueprint-managed groups.

## Deviations from Plan

**1. [Rule 3 - Blocking] Updated the job-list assertion in tests/test_ci_workflow.py**
- **Found during:** Task 1
- **Issue:** `test_workflow_has_exactly_python_and_web_jobs` asserted the jobs were exactly `["python", "web"]`, so adding the required `docker` job failed the plan's verify command.
- **Fix:** Renamed the test to `..._python_web_and_docker_jobs` and expected `["python", "web", "docker"]`, which is the plan's own acceptance criterion.
- **Files modified:** tests/test_ci_workflow.py
- **Commit:** 3c5843b

**Total deviations:** 1 auto-fixed (1 blocking). **Impact:** none beyond the intended job list.

## Verification

- `uv run pytest tests/test_deploy_config.py tests/test_ci_workflow.py -q`: 29 passed.
- `uv run ruff check .`: clean.
- `render blueprints validate render.yaml -o text`: `"valid": true` (after the Task 3 header edit).
- `js-yaml` parses `render.yaml` and `ci.yml`.
- Runbook topic check (`--dry-run`, `--once`, `--restore-crn`, `--remote-url`, `sync-status`, `Suspend`, `D-09`, `D-05`, `D-21`, `MIGRATION_DATABASE_URL`, `refresh_all_tampa`): all present.
- Secret scan: no connection string or credential value in render.yaml, Dockerfile, .dockerignore or the runbook.
- The Docker image itself is not built locally (Docker is not usable in this WSL distro). The first real build is the CI `docker` job on the first push (plan 09-14).

## Auth Gates

None.

## Known Stubs

None.

## Threat Flags

None. No new network endpoint, auth path or trust boundary beyond the plan's threat model (T-09-37 to T-09-41, T-09-SC), and each is covered by a test or CI check.

## Next Phase Readiness

Ready for 09-14 (first push, CI including the docker job, Render Blueprint creation). At Blueprint creation the operator must enter `DATABASE_URL` for api and worker, then fill `EASY_A_ALLOWED_FRONTEND_ORIGINS` and `VITE_API_BASE_URL` and redeploy the static site. Open owner decisions recorded in the runbook: Jan 7-15 contiguous window (OQ3), USF request volume (OQ8), cancelled-section display (OQ2).

## Self-Check: PASSED

Created files exist (Dockerfile, .dockerignore, render.yaml, tests/test_deploy_config.py, docs/runbooks/hosted-beta-operations.md); commits 3c5843b and 4d7ea79 exist.
