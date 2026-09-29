"""Static invariants for Dockerfile, .dockerignore, render.yaml and the CI docker job.

Stdlib only (PyYAML is not a project dependency), so these are substring and per-line
regex checks that tolerate formatting changes. Docker is not required.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile"
DOCKERIGNORE = ROOT / ".dockerignore"
RENDER = ROOT / "render.yaml"
CI = ROOT / ".github" / "workflows" / "ci.yml"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing file: {path}"
    return path.read_text(encoding="utf-8")


def _code_lines(path: Path) -> list[str]:
    """Non-comment, non-blank lines."""
    return [
        line
        for line in _read(path).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


# --- Dockerfile ---------------------------------------------------------------------------


def test_dockerfile_base_and_pinned_uv() -> None:
    text = _read(DOCKERFILE)
    assert re.search(r"^FROM python:3\.12-slim-trixie\s*$", text, re.MULTILINE)
    assert "COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /bin/" in text
    assert "uv sync --locked --no-dev" in text


def test_dockerfile_installs_tzdata_from_apt_not_pypi() -> None:
    text = _read(DOCKERFILE)
    assert "apt-get install -y --no-install-recommends tzdata" in text
    assert "rm -rf /var/lib/apt/lists/*" in text
    assert "pip install" not in text
    assert "uv add" not in text


def test_dockerfile_runs_as_non_root() -> None:
    users = [
        line.split(None, 1)[1].strip()
        for line in _code_lines(DOCKERFILE)
        if line.startswith("USER ")
    ]
    assert users, "no USER instruction"
    assert users[-1].lower() not in {"root", "0"}


def test_dockerfile_cmd_is_exec_form_uvicorn() -> None:
    cmd_lines = [line for line in _code_lines(DOCKERFILE) if line.startswith("CMD ")]
    assert len(cmd_lines) == 1
    cmd = cmd_lines[0]
    assert cmd.startswith('CMD ["sh", "-c", "exec uvicorn easy_a.api.app:app')
    assert "--host 0.0.0.0" in cmd
    assert "${PORT" in cmd
    assert "--no-access-log" in cmd


def test_dockerfile_copies_runtime_inputs() -> None:
    text = _read(DOCKERFILE)
    for needle in ("COPY src", "COPY config", "COPY migrations", "COPY alembic.ini"):
        assert needle in text, f"Dockerfile is missing: {needle}"
    assert "WORKDIR /app" in text


def test_dockerfile_has_no_secret_arg_or_env() -> None:
    for line in _code_lines(DOCKERFILE):
        if re.match(r"^(ARG|ENV)\b", line):
            upper = line.upper()
            assert "DATABASE_URL" not in upper, line
            assert "PASSWORD" not in upper, line
            assert "SECRET" not in upper, line
            assert "TOKEN" not in upper, line


# --- .dockerignore ------------------------------------------------------------------------

REQUIRED_IGNORES = (
    ".env",
    ".env.*",
    ".venv",
    ".git",
    "web/node_modules",
    "web/dist",
    "data/",
    "courses.csv",
    ".planning/",
    "*.xlsx",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "__pycache__",
    "*.pyc",
)
MUST_KEEP = (
    "README.md",
    "pyproject.toml",
    "uv.lock",
    "src",
    "config",
    "migrations",
    "alembic.ini",
)


def test_dockerignore_excludes_secrets_and_bulk() -> None:
    entries = {line.strip() for line in _code_lines(DOCKERIGNORE)}
    for required in REQUIRED_IGNORES:
        assert required in entries, f".dockerignore is missing: {required}"


def test_dockerignore_does_not_exclude_build_inputs() -> None:
    entries = {line.strip().rstrip("/") for line in _code_lines(DOCKERIGNORE)}
    for keep in MUST_KEEP:
        assert keep not in entries, f".dockerignore must not exclude {keep}"
        assert f"/{keep}" not in entries, f".dockerignore must not exclude /{keep}"


# --- render.yaml --------------------------------------------------------------------------


def test_render_declares_three_services() -> None:
    text = _read(RENDER)
    for name in ("easy-a-api", "easy-a-worker", "easy-a-web"):
        assert re.search(rf"^\s*name:\s*{name}\s*$", text, re.MULTILINE), name
    assert len(re.findall(r"^\s*autoDeployTrigger:\s*checksPass\s*$", text, re.MULTILINE)) == 3
    assert len(re.findall(r"^\s*region:\s*ohio\s*$", text, re.MULTILINE)) == 2


def test_render_api_and_worker_settings() -> None:
    text = _read(RENDER)
    assert re.search(r"^\s*healthCheckPath:\s*/health\s*$", text, re.MULTILINE)
    assert re.search(
        r"^\s*dockerCommand:\s*python -m easy_a\.sync --term 202701\s*$", text, re.MULTILINE
    )
    assert re.search(r"^\s*maxShutdownDelaySeconds:\s*90\s*$", text, re.MULTILINE)
    assert len(re.findall(r"^\s*plan:\s*starter\s*$", text, re.MULTILINE)) == 2


def test_render_static_site_settings() -> None:
    text = _read(RENDER)
    assert "buildCommand: cd web && npm ci && npm run build" in text
    assert re.search(r"^\s*staticPublishPath:\s*web/dist\s*$", text, re.MULTILINE)
    assert re.search(r"key:\s*VITE_USE_MOCK_DATA\s*\n\s*value:\s*\"false\"", text)
    assert re.search(r"key:\s*NODE_VERSION\s*\n\s*value:\s*\"24\"", text)
    assert "type: rewrite" in text
    assert re.search(r"^\s*destination:\s*/index\.html\s*$", text, re.MULTILINE)


def test_render_services_have_build_filters() -> None:
    text = _read(RENDER)
    assert len(re.findall(r"^\s*buildFilter:\s*$", text, re.MULTILINE)) == 3


def _env_var_blocks(text: str) -> list[tuple[str, list[str]]]:
    """(key, following lines up to the next list item) for every `- key:` entry."""
    lines = text.splitlines()
    blocks: list[tuple[str, list[str]]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^\s*-\s*key:\s*(\S+)\s*$", line)
        if not match:
            continue
        tail: list[str] = []
        for follower in lines[index + 1 :]:
            if re.match(r"^\s*-\s", follower) or not follower.strip():
                break
            tail.append(follower)
        blocks.append((match.group(1), tail))
    return blocks


def test_render_database_url_is_never_a_value() -> None:
    text = _read(RENDER)
    uses_group = re.search(r"fromGroup:\s*easy-a-shared", text) is not None
    blocks = [b for b in _env_var_blocks(text) if b[0] == "DATABASE_URL"]
    assert blocks, "no DATABASE_URL entry"
    for _key, tail in blocks:
        joined = "\n".join(tail)
        assert re.search(r"^\s*value:", joined, re.MULTILINE) is None
        if not uses_group:
            assert re.search(r"^\s*sync:\s*false\s*$", joined, re.MULTILINE), "needs sync: false"


def test_render_secret_and_circular_env_vars_are_not_valued() -> None:
    text = _read(RENDER)
    for key in (
        "DATABASE_URL",
        "MIGRATION_DATABASE_URL",
        "VITE_API_BASE_URL",
        "EASY_A_ALLOWED_FRONTEND_ORIGINS",
    ):
        for block_key, tail in _env_var_blocks(text):
            if block_key == key:
                joined = "\n".join(tail)
                assert re.search(r"^\s*value:", joined, re.MULTILINE) is None, key
    # A key line for MIGRATION_DATABASE_URL must not exist at all (migrations stay manual).
    assert not any(key == "MIGRATION_DATABASE_URL" for key, _ in _env_var_blocks(text))
    # No connection string anywhere in the file.
    assert not re.search(r"postgres(ql)?(\+\w+)?://", text)


def test_render_allowed_origins_and_api_url_are_sync_false() -> None:
    blocks = dict(_env_var_blocks(_read(RENDER)))
    for key in ("EASY_A_ALLOWED_FRONTEND_ORIGINS", "VITE_API_BASE_URL"):
        assert key in blocks
        assert any(re.match(r"^\s*sync:\s*false\s*$", line) for line in blocks[key]), key


# --- CI docker job ------------------------------------------------------------------------


def test_ci_has_docker_job_with_build() -> None:
    text = _read(CI)
    assert re.search(r"^  docker:\s*$", text, re.MULTILINE)
    assert "docker build -t easy-a:ci ." in text
    assert "python -m easy_a.sync --help" in text
    assert "import easy_a.api.app" in text
    assert "ZoneInfo('America/New_York')" in text
    assert "id -u" in text
