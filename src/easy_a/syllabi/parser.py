from __future__ import annotations

import hashlib
import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, ConfigDict, Field

from easy_a.syllabi.client import build_view_url, extract_document_id


class SyllabusParseError(ValueError):
    """Raised when published syllabus HTML lacks required metadata."""


class ParsedSyllabus(BaseModel):
    document_id: str = Field(min_length=1)
    term_name: str = Field(min_length=1)
    term_code: str = Field(min_length=6, max_length=6)
    subject: str = Field(min_length=1)
    course_number: str = Field(min_length=1)
    section_number: str = Field(min_length=1)
    crn: str = Field(min_length=1)
    instructor_raw: str | None
    organization: str | None
    title: str
    view_url: str
    print_url: str | None
    last_updated_at: datetime | None
    content_html: str
    content_text: str
    content_hash: str

    model_config = ConfigDict(frozen=True)


def parse_syllabus_html(
    html: str,
    *,
    document_id: str,
    view_url: str | None = None,
    organization: str | None = None,
    last_updated_at: datetime | None = None,
) -> ParsedSyllabus:
    normalized_document_id = extract_document_id(document_id)
    soup = BeautifulSoup(html, "lxml")
    subject = _required_block_value(soup, "subject_name").upper()
    course_number = _required_block_value(soup, "course_ca_30").upper()
    title = _required_block_value(soup, "section_ca_33")
    crn = _required_block_value(soup, "section_ca_7")
    section_number = _required_block_value(soup, "section_name")
    term_name = _required_block_value(soup, "term_name")
    content_text = normalize_content_text(soup.get_text(" ", strip=True))
    if not content_text:
        raise SyllabusParseError("Published syllabus HTML contains no text.")
    return ParsedSyllabus(
        document_id=normalized_document_id,
        term_name=term_name,
        term_code=_term_name_to_banner_code(term_name),
        subject=subject,
        course_number=course_number,
        section_number=section_number,
        crn=crn,
        instructor_raw=_extract_instructor(soup),
        organization=_optional_clean(organization),
        title=title,
        view_url=view_url or build_view_url(normalized_document_id),
        print_url=None,
        last_updated_at=last_updated_at,
        content_html=html,
        content_text=content_text,
        content_hash=hash_content_text(content_text),
    )


def normalize_content_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ").replace("\u200b", "")).strip()


def hash_content_text(content_text: str) -> str:
    normalized = normalize_content_text(content_text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _required_block_value(soup: BeautifulSoup, block_name: str) -> str:
    node = soup.find(attrs={"data-block-name": block_name})
    if not isinstance(node, Tag):
        raise SyllabusParseError(f"Missing Simple Syllabus metadata block {block_name!r}.")
    value = normalize_content_text(node.get_text(" ", strip=True))
    if not value:
        raise SyllabusParseError(f"Simple Syllabus metadata block {block_name!r} is empty.")
    return value


def _extract_instructor(soup: BeautifulSoup) -> str | None:
    instructor = soup.select_one(".instructor-component .cell-content")
    if isinstance(instructor, Tag):
        return _optional_clean(normalize_content_text(instructor.get_text(" ", strip=True)))
    return None


def _term_name_to_banner_code(term_name: str) -> str:
    match = re.fullmatch(r"(Spring|Summer|Fall)\s+(\d{4})", term_name, re.IGNORECASE)
    if match is None:
        raise SyllabusParseError(f"Unsupported Simple Syllabus term name {term_name!r}.")
    suffix = {"spring": "01", "summer": "05", "fall": "08"}[match.group(1).lower()]
    return f"{match.group(2)}{suffix}"


def _optional_clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = normalize_content_text(value)
    return cleaned or None
