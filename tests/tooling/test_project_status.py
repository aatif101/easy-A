"""Tests for the in-flight work report in `scripts/project_status.py`.

The load-bearing part is collision classification: a shared source or test file means two
people are building the same thing and work must stop, while a shared planning file usually
just means both recorded progress. Getting that split wrong either hides duplicate work or
cries wolf often enough that the report stops being read.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "project_status.py"


def load_module() -> ModuleType:
    """Import the script by path — `scripts/` is not an importable package."""
    spec = importlib.util.spec_from_file_location("project_status", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["project_status"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def status() -> ModuleType:
    return load_module()


def make_branch(status: ModuleType, name: str, author: str, files: set[str]):  # type: ignore[no-untyped-def]
    return status.Branch(
        ref=f"origin/{name}",
        author=author,
        date="2026-09-10",
        subject="subject",
        files=frozenset(files),
    )


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (".planning/STATE.md", True),
        (".planning/phases/01-PLAN.md", True),
        ("docs/final-mvp-plan.md", True),
        ("README.md", True),
        ("AGENTS.md", True),
        ("CLAUDE.md", True),
        ("src/easy_a/refresh/cleanup.py", False),
        ("tests/refresh/test_cleanup.py", False),
        ("scripts/cleanup_non_tampa_sections.py", False),
        ("web/src/App.tsx", False),
        # A markdown file nested under a code tree still is not behaviour, but it is also
        # not a planning document, so it must not silently downgrade a collision.
        ("src/easy_a/notes.md", False),
    ],
)
def test_is_prose_classifies_paths(status: ModuleType, path: str, expected: bool) -> None:
    assert status.is_prose(path) is expected


def test_shared_source_file_is_a_hard_collision(status: ModuleType) -> None:
    """The real 2026-09-10 incident: two branches, same cleanup module."""
    left = make_branch(
        status,
        "claude/main-branch-status-ya1inr",
        "Claude",
        {"src/easy_a/refresh/cleanup.py", "README.md", "src/easy_a/quality/checks.py"},
    )
    right = make_branch(
        status,
        "dev1/tampa-data-cleanup",
        "kanishk-sc",
        {"src/easy_a/refresh/cleanup.py", "README.md", "tests/refresh/test_cleanup.py"},
    )

    hard, soft = status.collisions([left, right])

    assert soft == []
    assert len(hard) == 1
    first, second, shared = hard[0]
    assert {first.author, second.author} == {"Claude", "kanishk-sc"}
    assert shared == frozenset({"src/easy_a/refresh/cleanup.py", "README.md"})


def test_shared_planning_file_only_is_a_soft_collision(status: ModuleType) -> None:
    """Two sessions both recording progress is expected, not a duplicate-work alarm."""
    left = make_branch(status, "dev1/a", "kanishk-sc", {".planning/STATE.md", "src/easy_a/db.py"})
    right = make_branch(status, "dev2/b", "aatif", {".planning/STATE.md", "web/src/App.tsx"})

    hard, soft = status.collisions([left, right])

    assert hard == []
    assert len(soft) == 1
    assert soft[0][2] == frozenset({".planning/STATE.md"})


def test_branches_touching_nothing_in_common_do_not_collide(status: ModuleType) -> None:
    left = make_branch(status, "dev1/backend", "kanishk-sc", {"src/easy_a/api/app.py"})
    right = make_branch(status, "dev2/frontend", "aatif", {"web/src/App.tsx"})

    assert status.collisions([left, right]) == ([], [])


def test_collisions_are_reported_widest_first(status: ModuleType) -> None:
    wide_a = make_branch(status, "dev1/wide-a", "kanishk-sc", {"a.py", "b.py", "c.py"})
    wide_b = make_branch(status, "dev1/wide-b", "aatif", {"a.py", "b.py", "c.py"})
    narrow = make_branch(status, "dev1/narrow", "Claude", {"a.py"})

    hard, _ = status.collisions([wide_a, wide_b, narrow])

    assert [len(shared) for _, _, shared in hard] == [3, 1, 1]


def test_a_single_branch_cannot_collide_with_itself(status: ModuleType) -> None:
    only = make_branch(status, "dev1/solo", "kanishk-sc", {"src/easy_a/refresh/cleanup.py"})

    assert status.collisions([only]) == ([], [])


def test_branch_short_name_strips_the_remote(status: ModuleType) -> None:
    branch = make_branch(status, "dev1/tampa-data-cleanup", "kanishk-sc", set())

    assert branch.short == "dev1/tampa-data-cleanup"


def test_pr_label_distinguishes_draft_and_missing_pull_requests(status: ModuleType) -> None:
    branch = make_branch(status, "dev1/x", "kanishk-sc", set())
    assert branch.pr_label == "no PR"

    branch.pr_number = 18
    branch.pr_draft = True
    assert branch.pr_label == "PR #18 (draft)"

    branch.pr_draft = False
    assert branch.pr_label == "PR #18"
