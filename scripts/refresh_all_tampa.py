from __future__ import annotations

import argparse
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from easy_a.refresh.targets import load_targets

DEFAULT_TARGETS = Path("config/course_targets.toml")
DEFAULT_PROGRESS = Path("refresh_all_tampa.progress")
DEFAULT_PACE_SECONDS = 2.0
# Per-subject wall-clock ceiling. A stalled subject (e.g. a hung DB operation with no
# statement timeout) must NOT freeze the whole sequential run; when a subject exceeds this,
# its subprocess is killed and the subject is recorded as failed so the run continues.
DEFAULT_SUBJECT_TIMEOUT_SECONDS = 900.0
# Sentinel returncode used when a subject is killed for exceeding --subject-timeout
# (mirrors the conventional GNU `timeout` exit status).
SUBJECT_TIMEOUT_RETURNCODE = 124


def enumerate_subjects(
    targets_path: Path, subjects: tuple[str, ...] | None = None
) -> tuple[str, ...]:
    """Distinct, sorted subjects from the committed target config; optionally filtered."""
    config = load_targets(targets_path)
    all_subjects = sorted({target.subject for target in config.targets})
    if subjects:
        wanted = {subject.strip().upper() for subject in subjects}
        return tuple(subject for subject in all_subjects if subject in wanted)
    return tuple(all_subjects)


def load_completed_subjects(progress_path: Path) -> set[str]:
    """Subjects already recorded as completed by a prior run (resume support)."""
    if not progress_path.exists():
        return set()
    return {
        line.strip()
        for line in progress_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def record_completed_subject(progress_path: Path, subject: str) -> None:
    """Append one completed subject to the progress file (only called on exit 0)."""
    with progress_path.open("a", encoding="utf-8") as fh:
        fh.write(f"{subject}\n")


def _run_subject(
    term: str,
    targets_path: Path,
    subject: str,
    *,
    timeout_seconds: float | None = None,
) -> int:
    """Invoke refresh_course_coverage.py for exactly one subject, as its own OS process and
    its own database transaction. No cross-subject transaction is ever opened here.

    When ``timeout_seconds`` is set and the subject exceeds it, the subprocess is killed and
    ``SUBJECT_TIMEOUT_RETURNCODE`` is returned so the caller records the subject as failed and
    moves on -- a hang on one subject never freezes the whole run."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/refresh_course_coverage.py",
                "--term",
                term,
                "--targets",
                str(targets_path),
                "--subject",
                subject,
            ],
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        print(
            f"Subject {subject} exceeded --subject-timeout ({timeout_seconds}s); "
            "killed and recorded as failed. Re-run to resume it.",
            file=sys.stderr,
        )
        return SUBJECT_TIMEOUT_RETURNCODE
    return result.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Resumable, paced orchestrator that drives refresh_course_coverage.py once per "
            "subject -- each subject its own process/transaction -- across the full Tampa "
            "target universe."
        )
    )
    parser.add_argument("--term", required=True, help="Banner term, e.g. 202701.")
    parser.add_argument(
        "--targets",
        type=Path,
        default=DEFAULT_TARGETS,
        help=f"Course targets TOML path (default {DEFAULT_TARGETS}).",
    )
    parser.add_argument(
        "--pace-seconds",
        type=float,
        default=DEFAULT_PACE_SECONDS,
        help=f"Delay between subject invocations, applied between subjects only, "
        f"not before the first (default {DEFAULT_PACE_SECONDS}).",
    )
    parser.add_argument(
        "--progress",
        type=Path,
        default=DEFAULT_PROGRESS,
        help=f"Progress file recording completed subjects for resume (default {DEFAULT_PROGRESS}).",
    )
    parser.add_argument(
        "--subject-timeout",
        type=float,
        default=DEFAULT_SUBJECT_TIMEOUT_SECONDS,
        help=f"Per-subject wall-clock ceiling in seconds (default {DEFAULT_SUBJECT_TIMEOUT_SECONDS}). "
        f"A subject exceeding this is killed and recorded as failed so the run continues; "
        f"0 or negative disables the ceiling.",
    )
    parser.add_argument(
        "--subjects",
        nargs="*",
        default=None,
        help="Optional explicit subject subset (default: every distinct subject in --targets).",
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> int:
    args = build_parser().parse_args(argv)
    requested_subjects = tuple(args.subjects) if args.subjects else None
    subjects = enumerate_subjects(args.targets, requested_subjects)
    already_done = load_completed_subjects(args.progress)

    subject_timeout = (
        args.subject_timeout if args.subject_timeout and args.subject_timeout > 0 else None
    )

    skipped = [subject for subject in subjects if subject in already_done]
    remaining = [subject for subject in subjects if subject not in already_done]

    completed: list[str] = []
    failed: list[str] = []

    for index, subject in enumerate(remaining):
        if index > 0:
            sleep_fn(args.pace_seconds)
        returncode = _run_subject(
            args.term, args.targets, subject, timeout_seconds=subject_timeout
        )
        if returncode == 0:
            record_completed_subject(args.progress, subject)
            completed.append(subject)
        else:
            failed.append(subject)

    print(f"Subjects total: {len(subjects)}")
    print(f"Completed this run: {len(completed)}")
    print(f"Already done (skipped): {len(skipped)}")
    print(f"Failed: {len(failed)}")
    if failed:
        print(f"Failed subjects: {', '.join(failed)}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
