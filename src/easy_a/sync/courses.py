"""Auto-add of undergraduate Tampa courses the sweep sees but Easy-A does not know yet (D-05).

For each new course the worker makes one bounded, paced catalog request (PROJECT.md D-09: no
crawling), parses it with the existing catalog parser and upserts only the exact
``(subject, number)`` match. It never writes ``config/course_targets.toml`` and never invents a
schedule-derived stand-in row: a made-up edition could sort above the real catalog edition in
``resolve_course_id`` and split one course into two rows (RESEARCH Pattern 10). An auto-added
course has no grade history, so its rankings carry the honest ``subject``/``global`` fallback
label with ``effective_n = 0`` (D-20); scoring is untouched (D-02).

This module must stay light: no pandas and nothing from ``easy_a.refresh`` (that package's
``__init__`` pulls pandas). The two catalog settings are read with ``tomllib`` instead.
"""

from __future__ import annotations

import time
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

import httpx
from sqlalchemy.orm import Session

from easy_a.catalog.client import fetch_catalog_html
from easy_a.catalog.ingest import upsert_catalog_courses
from easy_a.catalog.parser import CatalogParseError, parse_catalog_html
from easy_a.config import get_settings

CourseKey = tuple[str, str]

MAX_PER_SWEEP = 10
PACE_SECONDS = 2.0
RETRY_AFTER = timedelta(hours=6)
DEFERRED_REASON = "deferred: per-sweep cap"


class CatalogSettingsError(ValueError):
    """Raised when the catalog settings in course_targets.toml are missing or malformed."""


@dataclass(frozen=True)
class CatalogSettings:
    catalog_edition: str
    catalog_url_template: str

    def url_for(self, key: CourseKey) -> str:
        subject, number = key
        return self.catalog_url_template.format(subject=subject, number=number)


def load_catalog_settings(path: str | Path | None = None) -> CatalogSettings:
    """Read only ``catalog_edition`` and ``catalog_url_template`` from the targets file."""
    target = Path(path) if path is not None else Path(get_settings().course_targets_path)
    try:
        with target.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError as exc:
        raise CatalogSettingsError(f"cannot read catalog settings file {target}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise CatalogSettingsError(f"catalog settings file {target} is not valid TOML") from exc

    edition = data.get("catalog_edition")
    template = data.get("catalog_url_template")
    if not isinstance(edition, str) or not edition.strip():
        raise CatalogSettingsError(f"{target} is missing a non-empty catalog_edition")
    if not isinstance(template, str) or not template.strip():
        raise CatalogSettingsError(f"{target} is missing a non-empty catalog_url_template")
    if "{subject}" not in template or "{number}" not in template:
        raise CatalogSettingsError(
            f"catalog_url_template in {target} must contain {{subject}} and {{number}}"
        )
    settings = CatalogSettings(catalog_edition=edition.strip(), catalog_url_template=template)
    try:
        settings.url_for(("ABC", "1234"))
    except (KeyError, IndexError, ValueError) as exc:
        raise CatalogSettingsError(
            f"catalog_url_template in {target} has unsupported placeholders"
        ) from exc
    return settings


def label(key: CourseKey) -> str:
    return f"{key[0]} {key[1]}"


@dataclass(frozen=True)
class AutoAddResult:
    added: tuple[CourseKey, ...] = ()
    failed: tuple[tuple[CourseKey, str], ...] = ()
    deferred: tuple[CourseKey, ...] = ()

    def unapplied(self) -> dict[CourseKey, str]:
        """Every course that could not be added, with the reason to report."""
        reasons: dict[CourseKey, str] = dict(self.failed)
        for key in self.deferred:
            reasons[key] = DEFERRED_REASON
        return reasons


class CourseAdderLike(Protocol):
    """What the sweep needs from a course adder (a fake in tests, CourseAdder in production)."""

    def add_missing(self, session: Session, keys: Sequence[CourseKey]) -> AutoAddResult: ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(kw_only=True)
class CourseAdder:
    """Paced, capped catalog lookup for new courses, with a process-lifetime negative cache."""

    fetch: Callable[[str], str] | None = None
    sleep: Callable[[float], None] = time.sleep
    now_fn: Callable[[], datetime] = _utc_now
    settings: CatalogSettings | None = None
    max_per_sweep: int = MAX_PER_SWEEP
    pace_seconds: float = PACE_SECONDS
    retry_after: timedelta = RETRY_AFTER
    _failed_at: dict[CourseKey, datetime] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.fetch is None:
            self.fetch = fetch_catalog_html

    def add_missing(self, session: Session, keys: Sequence[CourseKey]) -> AutoAddResult:
        """Try to add each key (sorted order). The caller owns the transaction."""
        if not keys:
            return AutoAddResult()
        settings = self.settings or load_catalog_settings()
        self.settings = settings
        assert self.fetch is not None

        added: list[CourseKey] = []
        failed: list[tuple[CourseKey, str]] = []
        deferred: list[CourseKey] = []
        attempts = 0
        for key in sorted(set(keys)):
            now = self.now_fn()
            failed_at = self._failed_at.get(key)
            if failed_at is not None and now - failed_at < self.retry_after:
                until = (failed_at + self.retry_after).isoformat()
                failed.append((key, f"negative-cached until {until}"))
                continue
            if attempts >= self.max_per_sweep:
                deferred.append(key)
                continue
            if attempts > 0:
                self.sleep(self.pace_seconds)
            attempts += 1

            reason = self._try_add(session, settings, key)
            if reason is None:
                self._failed_at.pop(key, None)
                added.append(key)
            else:
                self._failed_at[key] = self.now_fn()
                failed.append((key, reason))
        return AutoAddResult(added=tuple(added), failed=tuple(failed), deferred=tuple(deferred))

    def _try_add(self, session: Session, settings: CatalogSettings, key: CourseKey) -> str | None:
        """Fetch, parse and upsert one course. Returns None on success, else the failure reason."""
        assert self.fetch is not None
        try:
            html = self.fetch(settings.url_for(key))
            parsed = parse_catalog_html(html, settings.catalog_edition)
        except CatalogParseError:
            return "no catalog heading"
        except httpx.HTTPError as exc:
            return f"fetch failed: {type(exc).__name__}"
        matching = [course for course in parsed if (course.subject, course.number) == key]
        if not matching:
            return f"catalog page did not describe {label(key)}"
        upsert_catalog_courses(session, matching)
        return None


_default_adder: CourseAdder | None = None


def default_course_adder() -> CourseAdder:
    """The worker-process singleton, so the negative cache outlives a single sweep."""
    global _default_adder
    if _default_adder is None:
        _default_adder = CourseAdder()
    return _default_adder


def reset_default_course_adder() -> None:
    """Drop the singleton (tests and settings reloads)."""
    global _default_adder
    _default_adder = None
