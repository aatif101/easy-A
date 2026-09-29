# One image, two processes (carried hosting decision): the default CMD runs the API; the
# Render worker overrides it with `python -m easy_a.sync --term 202701`.
FROM python:3.12-slim-trixie

# OS tz database for zoneinfo (America/New_York). Deliberately the Debian package, not the
# PyPI `tzdata` distribution: no new registry dependency.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependency layer first (README.md is read by hatchling at sync time).
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

# Relative paths in Settings (config/*.toml) resolve against WORKDIR /app.
COPY src ./src
COPY config ./config
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --locked --no-dev

# Unprivileged runtime user.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin easya
USER 10001

# Default = API. `exec` makes uvicorn PID 1 so it receives SIGTERM. Render sets PORT
# (default 10000). The app's own request log replaces uvicorn's access log.
CMD ["sh", "-c", "exec uvicorn easy_a.api.app:app --host 0.0.0.0 --port ${PORT:-10000} --no-access-log"]
