from __future__ import annotations

import pytest

from easy_a.refresh.cli import build_parser


def test_refresh_requires_explicit_term_even_with_grade_file() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--grade-file", "grades.xlsx"])


def test_grade_file_help_makes_exact_term_contract_explicit() -> None:
    help_text = build_parser().format_help()

    assert "grade workbook for exactly --term" in help_text
    assert "does not supply a trusted term" in help_text
