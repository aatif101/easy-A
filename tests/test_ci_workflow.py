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
