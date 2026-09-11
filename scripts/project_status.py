#!/usr/bin/env python3
"""Report where the project actually stands, including work already in flight.

Run this before starting any work. Planning files record what was true at the last
merge; unmerged branches and open pull requests record what someone is doing right
now. This command reads both and says so when they disagree.

    uv run python scripts/project_status.py

Only git is required. If the GitHub CLI (``gh``) is on PATH and authenticated,
pull request numbers and draft state are added to each in-flight branch.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

DEFAULT_REMOTE = "origin"
DEFAULT_BASE = "main"

# Branches that carry no project work and should never be reported as in flight.
IGNORED_BRANCH_SUFFIXES = ("/HEAD",)


class StatusError(RuntimeError):
    """A git command failed in a way that makes the report untrustworthy."""


def run_git(*args: str) -> str:
    """Run a git command and return stripped stdout, raising on failure."""
    result = subprocess.run(
        ("git", *args),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise StatusError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def try_git(*args: str) -> str | None:
    """Run a git command, returning None instead of raising when it fails."""
    try:
        return run_git(*args)
    except StatusError:
        return None


@dataclass
class Branch:
    """An unmerged remote branch — someone's in-flight work."""

    ref: str
    author: str
    date: str
    subject: str
    files: frozenset[str] = field(default_factory=frozenset)
    pr_number: int | None = None
    pr_draft: bool = False
    pr_title: str = ""

    @property
    def short(self) -> str:
        return self.ref.split("/", 1)[1] if "/" in self.ref else self.ref

    @property
    def pr_label(self) -> str:
        if self.pr_number is None:
            return "no PR"
        return f"PR #{self.pr_number}{' (draft)' if self.pr_draft else ''}"


def fetch(remote: str) -> bool:
    """Refresh remote refs. A failure is reported but not fatal — stale refs still inform."""
    return try_git("fetch", "--all", "--prune") is not None


def base_sha(remote: str, base: str) -> str:
    sha = try_git("rev-parse", f"{remote}/{base}")
    if sha is None:
        raise StatusError(f"cannot resolve {remote}/{base} — has the remote been fetched?")
    return sha


def unmerged_branches(remote: str, base: str) -> list[Branch]:
    """Every remote branch holding commits that are not yet in the base branch."""
    raw = run_git("branch", "-r", "--no-merged", f"{remote}/{base}")
    branches: list[Branch] = []
    for line in raw.splitlines():
        ref = line.strip()
        if not ref or ref.endswith(IGNORED_BRANCH_SUFFIXES) or "->" in ref:
            continue
        if ref == f"{remote}/{base}" or not ref.startswith(f"{remote}/"):
            continue
        meta = try_git("log", "-1", "--format=%an%x00%ad%x00%s", "--date=short", ref)
        author, date, subject = meta.split("\x00") if meta else ("?", "?", "?")
        files = try_git("diff", "--name-only", f"{remote}/{base}...{ref}")
        branches.append(
            Branch(
                ref=ref,
                author=author,
                date=date,
                subject=subject,
                files=frozenset(files.splitlines()) if files else frozenset(),
            )
        )
    branches.sort(key=lambda b: b.date, reverse=True)
    return branches


def attach_pull_requests(branches: list[Branch]) -> str | None:
    """Annotate branches with open PR data via gh. Returns a note when unavailable."""
    if shutil.which("gh") is None:
        return "gh not on PATH — pull request numbers omitted (branch data below is complete)"
    proc = subprocess.run(
        (
            "gh",
            "pr",
            "list",
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,title,headRefName,isDraft",
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return "gh could not list pull requests (not authenticated?) — numbers omitted"
    try:
        payload = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return "gh returned output that could not be parsed — numbers omitted"
    by_head = {item["headRefName"]: item for item in payload}
    for branch in branches:
        match = by_head.get(branch.short)
        if match:
            branch.pr_number = match["number"]
            branch.pr_draft = bool(match["isDraft"])
            branch.pr_title = match["title"]
    return None


def is_prose(path: str) -> bool:
    """True for files that carry no behaviour — planning, docs, top-level markdown."""
    return path.startswith((".planning/", "docs/")) or (path.endswith(".md") and "/" not in path)


Overlap = tuple[Branch, Branch, frozenset[str]]


def collisions(branches: list[Branch]) -> tuple[list[Overlap], list[Overlap]]:
    """Overlapping in-flight branches, split into code collisions and prose-only ones.

    A shared source or test file means two people are building the same thing. A shared
    planning file usually just means both recorded progress, which is expected.
    """
    hard: list[Overlap] = []
    soft: list[Overlap] = []
    for i, left in enumerate(branches):
        for right in branches[i + 1 :]:
            shared = left.files & right.files
            if not shared:
                continue
            bucket = soft if all(is_prose(path) for path in shared) else hard
            bucket.append((left, right, shared))
    hard.sort(key=lambda pair: len(pair[2]), reverse=True)
    soft.sort(key=lambda pair: len(pair[2]), reverse=True)
    return hard, soft


def next_action(remote: str, base: str) -> list[str]:
    """The Next Action section of STATE.md as it exists on the base branch."""
    text = try_git("show", f"{remote}/{base}:.planning/STATE.md")
    if text is None:
        return []
    match = re.search(r"^## Next Action\s*\n(.*?)(?=^## )", text, re.MULTILINE | re.DOTALL)
    if not match:
        return []
    lines = [line.rstrip() for line in match.group(1).strip().splitlines()]
    return lines


def local_state_differs(remote: str, base: str) -> bool:
    """True when the working copy of STATE.md differs from the base branch's.

    The report deliberately quotes the base branch, because that is what everyone else
    reads. An uncommitted or unpushed local edit is invisible to them until it merges.
    """
    diff = try_git("diff", f"{remote}/{base}", "--name-only", "--", ".planning/STATE.md")
    return bool(diff)


def state_staleness(remote: str, base: str) -> tuple[str | None, int]:
    """When STATE.md was last updated on the base branch, and commits landed since."""
    last = try_git(
        "log", "-1", "--format=%ad", "--date=short", f"{remote}/{base}", "--", ".planning/STATE.md"
    )
    if last is None:
        return None, 0
    since = try_git("rev-list", "--count", f"{remote}/{base}", f"--since={last}", "--", ".")
    try:
        return last, max(int(since or 0) - 1, 0)
    except ValueError:
        return last, 0


def rule(char: str = "-", width: int = 78) -> str:
    return char * width


def render(remote: str, base: str, fetched: bool) -> int:
    """Print the report. Returns the intended process exit code."""
    sha = base_sha(remote, base)
    branches = unmerged_branches(remote, base)
    pr_note = attach_pull_requests(branches)
    hard_overlaps, soft_overlaps = collisions(branches)

    print(rule("="))
    print("EASY-A PROJECT STATUS")
    print(rule("="))
    freshness = "fetched just now" if fetched else "FETCH FAILED - refs may be stale"
    print(f"{remote}/{base} = {sha[:7]}   ({freshness})")
    print()

    print(rule())
    print("IN FLIGHT RIGHT NOW — authoritative, cannot go stale")
    print(rule())
    if not branches:
        print(f"  Nothing in flight. Every remote branch is merged into {remote}/{base}.")
    else:
        for branch in branches:
            print(f"  {branch.short}")
            print(
                f"      {branch.author:<14} {branch.date}   {branch.pr_label}"
                f"   {len(branch.files)} file(s)"
            )
            print(f"      {branch.subject}")
        if pr_note:
            print(f"\n  note: {pr_note}")
    print()

    if hard_overlaps:
        print(rule("!"))
        print("STOP — TWO BRANCHES ARE BUILDING THE SAME THING")
        print(rule("!"))
        for left, right, shared in hard_overlaps:
            print(f"  {left.short}  <->  {right.short}")
            print(
                f"      {left.author} and {right.author} both changed {len(shared)} shared file(s):"
            )
            for path in sorted(shared):
                print(f"        {'      ' if is_prose(path) else 'CODE  '}{path}")
            print()
        print("  Do NOT start work touching these files. Agree on one branch first.")
        print()

    if soft_overlaps:
        print(rule())
        print("Overlapping planning files only (usually fine — both recorded progress)")
        print(rule())
        for left, right, shared in soft_overlaps:
            print(f"  {left.short} <-> {right.short}: {', '.join(sorted(shared))}")
        print()

    last_state, commits_since = state_staleness(remote, base)
    print(rule())
    print("PLANNED NEXT ACTION — from .planning/STATE.md, only as fresh as the last merge")
    print(rule())
    action = next_action(remote, base)
    if action:
        for line in action[:14]:
            print(f"  {line}")
        if len(action) > 14:
            print(f"  ... ({len(action) - 14} more lines — read .planning/STATE.md)")
    else:
        print("  Could not find a '## Next Action' section in .planning/STATE.md.")
    if last_state:
        print()
        print(
            f"  STATE.md last updated on {base}: {last_state}"
            + (f"  ({commits_since} commit(s) landed since)" if commits_since else "")
        )
    if local_state_differs(remote, base):
        print()
        print(f"  NOTE: your local .planning/STATE.md differs from {remote}/{base}.")
        print("        The text above is what everyone else reads. Your edit stays")
        print("        invisible to them until it merges.")
    if branches:
        print()
        print("  ^ Trust the IN FLIGHT list above over this text. Planning files describe")
        print("    merged reality; unmerged branches describe what someone is doing now.")
    print()

    print(rule("="))
    if hard_overlaps:
        print("VERDICT: duplicate work in progress. Resolve the overlap before writing code.")
        exit_code = 2
    elif branches:
        print("VERDICT: work is in flight. Read the branches above before claiming anything.")
        exit_code = 1
    else:
        print("VERDICT: clear. Claim the next action by pushing a branch before you build.")
        exit_code = 0
    print(rule("="))
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--remote", default=DEFAULT_REMOTE, help="Remote name.")
    parser.add_argument("--base", default=DEFAULT_BASE, help="Base branch name.")
    parser.add_argument(
        "--no-fetch", action="store_true", help="Skip the fetch and report on already-known refs."
    )
    parser.add_argument(
        "--exit-zero", action="store_true", help="Always exit 0, even when work is in flight."
    )
    args = parser.parse_args(argv)

    try:
        fetched = True if args.no_fetch else fetch(args.remote)
        code = render(args.remote, args.base, fetched and not args.no_fetch)
    except StatusError as error:
        print(f"error: {error}", file=sys.stderr)
        return 3
    return 0 if args.exit_zero else code


if __name__ == "__main__":
    raise SystemExit(main())
