from __future__ import annotations

import csv
from pathlib import Path

import pytest
from pydantic import ValidationError

from easy_a.refresh.targets import load_targets
from scripts.generate_tampa_targets import build_targets, main


def _write_csv(path: Path, rows: list[tuple[str, str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["subject", "number", "title"])
        writer.writerows(rows)


def test_generator_count_matches_csv_data_rows_and_preserves_catalog_metadata(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "courses.csv"
    _write_csv(
        csv_path,
        [
            ("MAC", "1105", "College Algebra"),
            ("ENC", "1101", "Composition I"),
            ("AMH", "2020", "US History"),
        ],
    )
    config = build_targets(csv_path, catalog_edition="2026-2027")
    assert len(config.targets) == 3
    assert config.catalog_edition == "2026-2027"
    assert config.catalog_url_template == (
        "https://cloud.usf.edu/academic-programs/details/prefix/{subject}/code/{number}"
    )


def test_base_and_suffix_courses_appear_as_separate_entries(tmp_path: Path) -> None:
    csv_path = tmp_path / "courses.csv"
    _write_csv(
        csv_path,
        [
            ("CHM", "2045", "General Chemistry I"),
            ("CHM", "2045L", "General Chemistry I Lab"),
        ],
    )
    config = build_targets(csv_path)
    subjects_numbers = {(t.subject, t.number) for t in config.targets}
    assert subjects_numbers == {("CHM", "2045"), ("CHM", "2045L")}
    assert len(config.targets) == 2


@pytest.mark.parametrize(
    "bad_row",
    [
        ("chm", "2045", "lowercase subject"),
        ("CHEMX", "2045", "too many letters subject"),
        ("CHM", "204", "3-digit number"),
        ("CHM", "2045LL", "two trailing letters"),
    ],
)
def test_malformed_rows_raise_instead_of_dropping(
    tmp_path: Path, bad_row: tuple[str, str, str]
) -> None:
    csv_path = tmp_path / "courses.csv"
    _write_csv(csv_path, [bad_row])
    with pytest.raises(ValidationError):
        build_targets(csv_path)


def test_duplicate_subject_number_raises(tmp_path: Path) -> None:
    csv_path = tmp_path / "courses.csv"
    _write_csv(
        csv_path,
        [
            ("CHM", "2045", "General Chemistry I"),
            ("CHM", "2045", "Duplicate row"),
        ],
    )
    with pytest.raises(ValueError, match="Duplicate course targets."):
        build_targets(csv_path)


def test_regeneration_is_byte_identical(tmp_path: Path) -> None:
    csv_path = tmp_path / "courses.csv"
    _write_csv(
        csv_path,
        [
            ("MAC", "1105", "College Algebra"),
            ("ENC", "1101", "Composition I"),
            ("CHM", "2045", "General Chemistry I"),
            ("CHM", "2045L", "General Chemistry I Lab"),
        ],
    )
    out1 = tmp_path / "out1.toml"
    out2 = tmp_path / "out2.toml"
    assert main(["--csv", str(csv_path), "--out", str(out1)]) == 0
    assert main(["--csv", str(csv_path), "--out", str(out2)]) == 0
    assert out1.read_bytes() == out2.read_bytes()


def test_generated_toml_round_trips_through_load_targets(tmp_path: Path) -> None:
    csv_path = tmp_path / "courses.csv"
    _write_csv(
        csv_path,
        [
            ("CHM", "2045", "General Chemistry I"),
            ("CHM", "2045L", "General Chemistry I Lab"),
        ],
    )
    out_path = tmp_path / "targets.toml"
    assert main(["--csv", str(csv_path), "--out", str(out_path)]) == 0
    loaded = load_targets(out_path)
    assert len(loaded.targets) == 2
    assert {(t.subject, t.number) for t in loaded.targets} == {
        ("CHM", "2045"),
        ("CHM", "2045L"),
    }
