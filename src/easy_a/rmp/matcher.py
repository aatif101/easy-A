"""Match a USF schedule name (``N. Volz``) in one subject to a single Rate My Professors profile.

Pure logic, no I/O. The schedule gives only an initial and a last name, so a profile is accepted
only when the evidence points at exactly one person; everything else gets no profile and the
frontend falls back to a last-name search. Only the profile's ``legacyId`` leaves this module
(PROJECT.md D-08: no ratings, review counts, text, tags or summaries are imported).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

# USF course prefixes are three letters; RMP course codes are free text typed by students
# ("ENC1101", "enc 1102", "1101"), so only a leading three-letter prefix followed by a digit counts.
_COURSE_PREFIX = re.compile(r"^([A-Z]{3})\s*-?\s*\d")
_INITIAL = re.compile(r"^[A-Za-z]\.?$")
# The USF schedule cuts names at 18 characters ("K. Mavridou-Hernan"); the surname's tail is lost.
SCHEDULE_NAME_MAX = 18


class MatchMethod(StrEnum):
    course_code = "course_code"
    unique = "unique"
    override = "override"


@dataclass(frozen=True)
class RmpTeacher:
    legacy_id: int
    first_name: str
    last_name: str
    department: str
    course_codes: tuple[str, ...]
    # Used only to pick between duplicate profiles of the same person; never stored.
    num_ratings: int = 0

    @property
    def course_prefixes(self) -> frozenset[str]:
        prefixes = set()
        for code in self.course_codes:
            found = _COURSE_PREFIX.match(code.strip().upper())
            if found:
                prefixes.add(found.group(1))
        return frozenset(prefixes)


@dataclass(frozen=True)
class ParsedName:
    initial: str | None
    last_name: str
    truncated: bool = False

    @property
    def last_key(self) -> str:
        return fold(self.last_name)

    @property
    def search_text(self) -> str:
        """What to ask RMP: the surname, minus a cut-off last piece when the name was truncated."""
        if not self.truncated:
            return self.last_name
        pieces = re.split(r"[\s-]+", self.last_name)
        return " ".join(pieces[:-1]) if len(pieces) > 1 else self.last_name

    def matches_last_name(self, rmp_last_name: str) -> bool:
        rmp_key = fold(rmp_last_name)
        return rmp_key.startswith(self.last_key) if self.truncated else rmp_key == self.last_key


@dataclass(frozen=True)
class Match:
    legacy_id: int
    method: MatchMethod


def fold(value: str) -> str:
    """Accent-, case- and punctuation-insensitive key: ``D'Ávila-Ruiz`` -> ``davilaruiz``."""
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if ch.isalpha()).casefold()


def link_key(subject: str, name: str) -> str:
    """The shared lookup key; web/src/lib/rmp.ts builds the same string."""
    return f"{subject.strip().upper()}|{' '.join(name.split()).casefold()}"


def parse_name(name: str) -> ParsedName | None:
    """``N. Volz`` -> (n, Volz); ``J. A. Smith`` -> (j, Smith); ``Volz`` -> (None, Volz)."""
    tokens = name.split()
    initials: list[str] = []
    while tokens and _INITIAL.match(tokens[0]) and len(tokens) > 1:
        initials.append(tokens.pop(0)[0].casefold())
    last_name = " ".join(tokens)
    if not fold(last_name):
        return None
    return ParsedName(
        initial=initials[0] if initials else None,
        last_name=last_name,
        truncated=len(" ".join(name.split())) >= SCHEDULE_NAME_MAX,
    )


def _candidates(parsed: ParsedName, teachers: Iterable[RmpTeacher]) -> list[RmpTeacher]:
    matching = [
        teacher
        for teacher in teachers
        if parsed.matches_last_name(teacher.last_name)
        and (parsed.initial is None or fold(teacher.first_name)[:1] == parsed.initial)
    ]
    # RMP often holds duplicate profiles for one person; keep the most-rated of each full name.
    best: dict[str, RmpTeacher] = {}
    for teacher in matching:
        key = fold(teacher.first_name) + "|" + fold(teacher.last_name)
        if key not in best or teacher.num_ratings > best[key].num_ratings:
            best[key] = teacher
    return list(best.values())


def match_teacher(
    name: str,
    subject: str,
    teachers: Iterable[RmpTeacher],
    *,
    name_subjects: Iterable[str] = (),
) -> Match | None:
    """The single profile this instructor most plausibly is, or None when unsure.

    ``name_subjects`` is every subject this name teaches at USF; it widens the course-code
    evidence when RMP students rated the person under a different course.
    """
    parsed = parse_name(name)
    if parsed is None:
        return None
    candidates = _candidates(parsed, teachers)
    subject = subject.strip().upper()
    all_subjects = {subject, *(s.strip().upper() for s in name_subjects)}

    for subjects in ({subject}, all_subjects):
        evidenced = [c for c in candidates if c.course_prefixes & subjects]
        if len(evidenced) == 1:
            return Match(evidenced[0].legacy_id, MatchMethod.course_code)
        if len(evidenced) > 1:
            return None

    # One possible person, and nothing in RMP says they teach something else entirely.
    if len(candidates) == 1 and not candidates[0].course_prefixes:
        return Match(candidates[0].legacy_id, MatchMethod.unique)
    return None


def apply_overrides(
    matches: Mapping[str, Match | None],
    overrides: Mapping[str, int | None],
) -> dict[str, Match | None]:
    """Owner overrides win: an id forces that profile, ``None`` blocks a wrong auto-match."""
    merged = dict(matches)
    for key, legacy_id in overrides.items():
        merged[key] = None if legacy_id is None else Match(legacy_id, MatchMethod.override)
    return merged
