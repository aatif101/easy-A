from __future__ import annotations

import pytest

from easy_a.refresh.cli import build_parser


def test_refresh_requires_explicit_term_even_with_grade_file() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--grade-file", "grades.xlsx"])
