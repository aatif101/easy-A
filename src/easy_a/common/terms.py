from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class TermParseError(ValueError):
    """Raised when a Banner term code cannot be normalized."""


class Season(StrEnum):
    spring = "Spring"
    summer = "Summer"
    fall = "Fall"


_TERM_SUFFIX_TO_SEASON = {
    "01": Season.spring,
    "05": Season.summer,
    "08": Season.fall,
}


class TermInfo(BaseModel):
    banner_code: str
    name: str
    year: int
    season: Season

    model_config = ConfigDict(frozen=True)


def normalize_banner_term_code(value: str | int) -> str:
    term_code = str(value).strip()
    if len(term_code) != 6 or not term_code.isdigit():
        raise TermParseError(f"Banner term code must be six digits, got {value!r}.")
    if term_code[-2:] not in _TERM_SUFFIX_TO_SEASON:
        known_suffixes = ", ".join(sorted(_TERM_SUFFIX_TO_SEASON))
        raise TermParseError(
            f"Unsupported Banner term suffix {term_code[-2:]!r}; expected one of {known_suffixes}."
        )
    return term_code


def parse_banner_term(value: str | int) -> TermInfo:
    banner_code = normalize_banner_term_code(value)
    year = int(banner_code[:4])
    season = _TERM_SUFFIX_TO_SEASON[banner_code[-2:]]
    return TermInfo(
        banner_code=banner_code,
        name=f"{season.value} {year}",
        year=year,
        season=season,
    )


def coerce_banner_term(value: Any) -> TermInfo:
    if isinstance(value, str | int):
        return parse_banner_term(value)
    raise TermParseError(
        f"Banner term code must be a string or integer, got {type(value).__name__}."
    )
