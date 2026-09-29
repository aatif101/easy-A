"""Structural invariants of .github/workflows/ci.yml.

Stdlib only (PyYAML is not a project dependency), so these are substring and
per-line regex checks that tolerate formatting changes.
"""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
POSTGRES_URL = "postgresql+psycopg://easy_a:easy_a@localhost:5432/easy_a"


def _text() -> str:
    assert WORKFLOW.is_file(), f"missing workflow file: {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")


def _lines() -> list[str]:
    return _text().splitlines()


def test_workflow_file_exists() -> None:
    assert WORKFLOW.is_file()


def test_required_commands_and_pins_present() -> None:
    text = _text()
    for needle in (
        "astral-sh/setup-uv@v10.2.0",
        "actions/checkout@v7",
        "postgres:16",
        f"EASY_A_TEST_POSTGRES_URL: {POSTGRES_URL}",
        "uv run ruff check .",
        "uv run alembic upgrade head",
        "uv run alembic downgrade -1",
        "uv run pytest -q -rs",
        "Set EASY_A_TEST_POSTGRES_URL",
    ):
        assert needle in text, f"workflow is missing: {needle}"


def test_setup_uv_is_pinned_to_an_exact_tag() -> None:
    for line in _lines():
        if "astral-sh/setup-uv@" in line:
            assert re.search(r"astral-sh/setup-uv@v\d+\.\d+\.\d+\b", line), line


def test_token_is_read_only() -> None:
    assert re.search(r"^permissions:\s*\n\s+contents:\s*read\s*$", _text(), re.MULTILINE)


def test_no_path_filters() -> None:
    for line in _lines():
        assert not re.match(r"^\s*paths(-ignore)?\s*:", line), f"path filter found: {line}"


def test_triggers_cover_every_push_and_pull_request() -> None:
    text = _text()
    assert re.search(r"^\s*push:\s*$", text, re.MULTILINE)
    assert re.search(r"^\s*pull_request:\s*$", text, re.MULTILINE)
    assert re.search(r"""^\s*-\s*["']\*\*["']\s*$""", text, re.MULTILINE)


def test_no_secrets_and_no_hosted_database_url() -> None:
    text = _text()
    assert "secrets." not in text
    assert "${{ secrets" not in text
    # MIGRATION_DATABASE_URL / EASY_A_TEST_POSTGRES_URL are the local service container;
    # a bare DATABASE_URL would be the hosted Supabase connection.
    assert not re.search(r"(?<![A-Z_])DATABASE_URL", text)


def test_main_runs_are_never_cancelled() -> None:
    cancel_lines = [line for line in _lines() if "cancel-in-progress" in line]
    assert cancel_lines
    assert any("refs/heads/main" in line for line in cancel_lines)


def _steps() -> list[tuple[str, str]]:
    """Return (name, block) for each `- name:` step, blocks split between consecutive steps."""
    steps: list[tuple[str, str]] = []
    current_name: str | None = None
    current: list[str] = []
    for line in _lines():
        match = re.match(r"^\s*-\s+name:\s*(.+?)\s*$", line)
        if match:
            if current_name is not None:
                steps.append((current_name, "\n".join(current)))
            current_name = match.group(1)
            current = [line]
        elif current_name is not None:
            # a new job header (two-space-indented key) ends the last step of the previous job
            if re.match(r"^  \S", line) and not line.startswith("   "):
                steps.append((current_name, "\n".join(current)))
                current_name = None
                current = []
            else:
                current.append(line)
    if current_name is not None:
        steps.append((current_name, "\n".join(current)))
    return steps


def _job_names() -> list[str]:
    in_jobs = False
    names: list[str] = []
    for line in _lines():
        if re.match(r"^jobs:\s*$", line):
            in_jobs = True
            continue
        if in_jobs:
            match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
            if match:
                names.append(match.group(1))
            elif re.match(r"^\S", line):
                break
    return names


def test_workflow_has_exactly_python_and_web_jobs() -> None:
    assert _job_names() == ["python", "web"]


def test_web_job_runs_every_frontend_gate() -> None:
    text = _text()
    for needle in (
        "npm ci",
        "npm run lint",
        "npm run typecheck",
        "npm test",
        "npm run build",
        "actions/setup-node@v7",
        'node-version: "24"',
        "working-directory: web",
    ):
        assert needle in text, f"workflow is missing: {needle}"


def test_web_build_uses_real_api_mode() -> None:
    build = [block for _, block in _steps() if "npm run build" in block]
    assert build, "no web build step"
    assert 'VITE_USE_MOCK_DATA: "false"' in build[0]
    assert re.search(r'VITE_API_BASE_URL:\s*"https://', build[0])


def test_mypy_steps_are_report_only() -> None:
    mypy_blocks = [block for _, block in _steps() if re.search(r"run:.*\buv run mypy\b", block)]
    commands = " ".join(mypy_blocks)
    assert "uv run mypy src" in commands
    assert "uv run mypy ." in commands
    assert len(mypy_blocks) == 2
    for block in mypy_blocks:
        assert "continue-on-error: true" in block, block


def test_hard_gates_are_not_continue_on_error() -> None:
    hard = [
        (name, block)
        for name, block in _steps()
        if re.search(
            r"uv run ruff check|uv run pytest|must not skip|npm run lint|npm run typecheck"
            r"|npm test|npm run build",
            name + "\n" + block,
        )
    ]
    assert len(hard) >= 5
    for name, block in hard:
        assert "continue-on-error" not in block, f"hard gate is report-only: {name}"
