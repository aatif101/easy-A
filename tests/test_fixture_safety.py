from __future__ import annotations

from pathlib import Path


def test_no_raw_spreadsheet_exports_are_committed_as_fixtures() -> None:
    fixture_root = Path(__file__).parent / "fixtures"
    spreadsheet_exports = [
        path
        for path in fixture_root.rglob("*")
        if path.is_file() and path.suffix.casefold() in {".xls", ".xlsx"}
    ]

    assert spreadsheet_exports == []
