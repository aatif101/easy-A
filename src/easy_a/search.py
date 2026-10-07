"""Database search normalization. No guessed aliases or expanded instructor initials."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import SQLColumnExpression, and_, func, or_
from sqlalchemy.sql.elements import ColumnElement

PUNCTUATION = ".,;:-_/()[]'’\"\t\n"
# Title tokens only: numbered sequences in real catalog titles, never invented course aliases.
NUMERALS = {"1": "i", "2": "ii", "3": "iii", "4": "iv"}


@dataclass(frozen=True)
class SearchQuery:
    kind: str
    text: str
    subject: str = ""
    number: str = ""


def normalize_text(value: str) -> str:
    return " ".join(
        value.lower().translate(str.maketrans(PUNCTUATION, " " * len(PUNCTUATION))).split()
    )


def parse_query(value: str) -> SearchQuery:
    text = normalize_text(value)
    compact = text.replace(" ", "")
    if re.fullmatch(r"\d{5}", compact):
        return SearchQuery("crn", compact)
    code = re.fullmatch(r"([a-z]{3})(\d{4}[a-z]?)", compact)
    if code:
        return SearchQuery("course", text, code[1].upper(), code[2].upper())
    if re.fullmatch(r"\d{4}[a-z]?", compact):
        return SearchQuery("number", text, number=compact.upper())
    if re.fullmatch(r"[a-z]{3}", compact):
        return SearchQuery("subject", text, subject=compact.upper())
    return SearchQuery("text" if text else "empty", text)


def searchable(column: SQLColumnExpression[Any]) -> ColumnElement[Any]:
    result = func.lower(column)
    for char in PUNCTUATION:
        result = func.replace(result, char, " ")
    # Collapse reasonable spacing variations, on SQLite and PostgreSQL alike.
    for _ in range(5):
        result = func.replace(result, "  ", " ")
    return result


def text_match(
    column: SQLColumnExpression[Any], text: str, *, title: bool = False
) -> ColumnElement[bool]:
    # Each typed word must start a word: "yan" finds Yang, never Bryant; "cal" finds Calculus,
    # never Clinical. Punctuation is already spaces, so "lopez" starts a word of Garcia-Lopez.
    padded = " " + searchable(column)
    predicates = []
    for token in text.split():
        alternatives = [padded.contains(f" {token}", autoescape=True)]
        if title:
            numeric = next((n for n, roman in NUMERALS.items() if roman == token), token)
            if numeric in NUMERALS:
                # Whole tokens keep Calculus I distinct from Calculus II / III.
                alternatives = [
                    (padded + " ").contains(f" {variant} ", autoescape=True)
                    for variant in (numeric, NUMERALS[numeric])
                ]
        predicates.append(or_(*alternatives))
    return and_(*predicates)
