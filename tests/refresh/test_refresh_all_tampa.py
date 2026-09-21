from __future__ import annotations

from pathlib import Path

import pytest

from scripts import refresh_all_tampa

CATALOG_URL_TEMPLATE = (
    "https://cloud.usf.edu/academic-programs/details/prefix/{subject}/code/{number}"
)


def _write_targets(path: Path, subjects: list[str]) -> Path:
    """Write a minimal, validation-clean CourseTargets TOML with one target per subject."""
    lines = [
        'catalog_edition = "2026-2027"',
        f'catalog_url_template = "{CATALOG_URL_TEMPLATE}"',
        "",
    ]
    for index, subject in enumerate(subjects):
        lines.append("[[targets]]")
        lines.append(f'subject = "{subject}"')
        lines.append(f'number = "{1000 + index}"')
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_invokes_refresh_course_coverage_once_per_subject_with_correct_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    targets_path = _write_targets(tmp_path / "targets.toml", ["ENC", "MAC", "PSY"])
    progress_path = tmp_path / "progress.txt"
    calls: list[tuple[str, Path, str]] = []

    def fake_run_subject(term: str, targets: Path, subject: str) -> int:
        calls.append((term, targets, subject))
        return 0

    monkeypatch.setattr(refresh_all_tampa, "_run_subject", fake_run_subject)
    exit_code = refresh_all_tampa.main(
        [
            "--term",
            "202701",
            "--targets",
            str(targets_path),
            "--progress",
            str(progress_path),
        ],
        sleep_fn=lambda seconds: None,
    )
    assert exit_code == 0
    # Distinct subjects, sorted, one invocation each, carrying term/targets/subject through.
    assert calls == [
        ("202701", targets_path, "ENC"),
        ("202701", targets_path, "MAC"),
        ("202701", targets_path, "PSY"),
    ]


def test_run_subject_shells_out_to_refresh_course_coverage_with_correct_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    targets_path = tmp_path / "targets.toml"
    targets_path.write_text("placeholder", encoding="utf-8")
    captured_cmd: list[str] = []
    captured_check: list[bool] = []

    class _FakeCompletedProcess:
        returncode = 0

    def fake_run(cmd: list[str], *, check: bool) -> _FakeCompletedProcess:
        captured_cmd.extend(cmd)
        captured_check.append(check)
        return _FakeCompletedProcess()

    monkeypatch.setattr("scripts.refresh_all_tampa.subprocess.run", fake_run)
    returncode = refresh_all_tampa._run_subject("202701", targets_path, "MAC")

    assert returncode == 0
    assert captured_check == [False]
    assert "scripts/refresh_course_coverage.py" in captured_cmd
    assert captured_cmd[captured_cmd.index("--term") + 1] == "202701"
    assert captured_cmd[captured_cmd.index("--targets") + 1] == str(targets_path)
    assert captured_cmd[captured_cmd.index("--subject") + 1] == "MAC"


def test_paces_between_subjects_not_before_the_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    targets_path = _write_targets(tmp_path / "targets.toml", ["ENC", "MAC", "PSY"])
    progress_path = tmp_path / "progress.txt"
    sleeps: list[float] = []

    monkeypatch.setattr(refresh_all_tampa, "_run_subject", lambda *args, **kwargs: 0)
    exit_code = refresh_all_tampa.main(
        [
            "--term",
            "202701",
            "--targets",
            str(targets_path),
            "--progress",
            str(progress_path),
            "--pace-seconds",
            "5",
        ],
        sleep_fn=sleeps.append,
    )
    assert exit_code == 0
    # 3 subjects -> 2 pacing sleeps, each with the configured pace-seconds; none before the first.
    assert sleeps == [5.0, 5.0]


def test_progress_file_append_and_resume_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    targets_path = _write_targets(tmp_path / "targets.toml", ["ENC", "MAC"])
    progress_path = tmp_path / "progress.txt"
    calls: list[str] = []

    def fake_run_subject(term: str, targets: Path, subject: str) -> int:
        calls.append(subject)
        return 0

    monkeypatch.setattr(refresh_all_tampa, "_run_subject", fake_run_subject)

    first_exit = refresh_all_tampa.main(
        ["--term", "202701", "--targets", str(targets_path), "--progress", str(progress_path)],
        sleep_fn=lambda seconds: None,
    )
    assert first_exit == 0
    assert calls == ["ENC", "MAC"]
    assert progress_path.read_text(encoding="utf-8").splitlines() == ["ENC", "MAC"]

    calls.clear()
    second_exit = refresh_all_tampa.main(
        ["--term", "202701", "--targets", str(targets_path), "--progress", str(progress_path)],
        sleep_fn=lambda seconds: None,
    )
    assert second_exit == 0
    # Both subjects already recorded in the progress file -> resume run invokes neither.
    assert calls == []


def test_failed_subject_is_recorded_and_run_continues_not_aborts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    targets_path = _write_targets(tmp_path / "targets.toml", ["ENC", "MAC", "PSY"])
    progress_path = tmp_path / "progress.txt"
    calls: list[str] = []

    def fake_run_subject(term: str, targets: Path, subject: str) -> int:
        calls.append(subject)
        return 1 if subject == "MAC" else 0

    monkeypatch.setattr(refresh_all_tampa, "_run_subject", fake_run_subject)
    exit_code = refresh_all_tampa.main(
        ["--term", "202701", "--targets", str(targets_path), "--progress", str(progress_path)],
        sleep_fn=lambda seconds: None,
    )

    assert exit_code == 1
    # All three subjects were attempted -- the MAC failure did not abort the run.
    assert calls == ["ENC", "MAC", "PSY"]
    # Only the successful subjects were recorded as completed; MAC is not marked done.
    assert progress_path.read_text(encoding="utf-8").splitlines() == ["ENC", "PSY"]


def test_final_summary_reports_completed_skipped_and_failed_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    targets_path = _write_targets(tmp_path / "targets.toml", ["ENC", "MAC", "PSY"])
    progress_path = tmp_path / "progress.txt"
    progress_path.write_text("ENC\n", encoding="utf-8")

    def fake_run_subject(term: str, targets: Path, subject: str) -> int:
        return 1 if subject == "PSY" else 0

    monkeypatch.setattr(refresh_all_tampa, "_run_subject", fake_run_subject)
    exit_code = refresh_all_tampa.main(
        ["--term", "202701", "--targets", str(targets_path), "--progress", str(progress_path)],
        sleep_fn=lambda seconds: None,
    )
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Subjects total: 3" in output
    assert "Completed this run: 1" in output
    assert "Already done (skipped): 1" in output
    assert "Failed: 1" in output
    assert "PSY" in output
