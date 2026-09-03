from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from pathlib import Path

from easy_a.common.terms import normalize_banner_term_code
from easy_a.quality.models import QualityReport
from easy_a.syllabi.client import extract_document_id


class RefreshConfigurationError(ValueError):
    """Raised when a refresh source is incomplete or internally inconsistent."""


class SourceMode(StrEnum):
    live = "live"
    file = "file"


@dataclass(frozen=True)
class CatalogInput:
    source: SourceMode
    catalog_edition: str
    url: str | None = None
    file_path: Path | None = None

    def __post_init__(self) -> None:
        edition = self.catalog_edition.strip()
        if not edition:
            raise RefreshConfigurationError("Catalog edition is required for catalog refresh.")
        object.__setattr__(self, "catalog_edition", edition)
        if self.source is SourceMode.live:
            if not self.url or not self.url.strip():
                raise RefreshConfigurationError("Live catalog refresh requires a catalog URL.")
            if self.file_path is not None:
                raise RefreshConfigurationError("Live catalog refresh cannot also use a file.")
        elif self.file_path is None:
            raise RefreshConfigurationError("File catalog refresh requires an HTML file.")
        elif self.url is not None:
            raise RefreshConfigurationError("File catalog refresh cannot also use a URL.")


@dataclass(frozen=True)
class ScheduleInput:
    source: SourceMode
    file_path: Path | None = None
    campus: str | None = None
    subject: str | None = None
    course: str | None = None
    crn: str | None = None

    def __post_init__(self) -> None:
        if self.source is SourceMode.file:
            if self.file_path is None:
                raise RefreshConfigurationError("File schedule refresh requires an HTML file.")
            query_values = (self.campus, self.subject, self.course, self.crn)
            if any(value is not None for value in query_values):
                raise RefreshConfigurationError(
                    "Schedule query fields apply only to a live schedule source."
                )
            return
        if self.file_path is not None:
            raise RefreshConfigurationError("Live schedule refresh cannot also use a file.")
        if not _has_text(self.subject) and not _has_text(self.crn):
            raise RefreshConfigurationError(
                "Live schedule refresh requires a subject or CRN for a narrow search."
            )


@dataclass(frozen=True)
class GradeInput:
    file_path: Path


@dataclass(frozen=True)
class SyllabusFileInput:
    document_id: str
    file_path: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_id", extract_document_id(self.document_id))


@dataclass(frozen=True)
class SyllabusInput:
    source: SourceMode
    documents: tuple[str, ...] = ()
    files: tuple[SyllabusFileInput, ...] = ()

    def __post_init__(self) -> None:
        if self.source is SourceMode.live:
            if not self.documents:
                raise RefreshConfigurationError(
                    "Live syllabus refresh requires at least one document ID or URL."
                )
            if self.files:
                raise RefreshConfigurationError("Live syllabus refresh cannot also use files.")
            return
        if not self.files:
            raise RefreshConfigurationError(
                "File syllabus refresh requires at least one DOCUMENT_ID=HTML mapping."
            )
        if self.documents:
            raise RefreshConfigurationError("File syllabus refresh cannot use live documents.")


@dataclass(frozen=True)
class RefreshConfig:
    term: str
    catalog: CatalogInput | None = None
    schedule: ScheduleInput | None = None
    grades: GradeInput | None = None
    syllabi: SyllabusInput | None = None
    stale_after: timedelta = timedelta(days=7)

    def __post_init__(self) -> None:
        object.__setattr__(self, "term", normalize_banner_term_code(self.term))
        if self.stale_after.total_seconds() < 0:
            raise RefreshConfigurationError("Stale observation threshold must be non-negative.")


@dataclass(frozen=True)
class RefreshResult:
    term: str
    courses: int
    sections: int
    instructor_observations_added: int
    seat_snapshots_added: int
    grade_rows: int
    syllabi: int
    quality_report: QualityReport


def _has_text(value: str | None) -> bool:
    return value is not None and bool(value.strip())
