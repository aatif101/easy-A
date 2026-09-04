from __future__ import annotations

import re
from collections.abc import Iterable

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CatalogParseError(ValueError):
    """Raised when catalog HTML does not contain parseable course records."""


class CatalogAttribute(BaseModel):
    attribute_code: str = Field(min_length=1)
    attribute_label: str = Field(min_length=1)

    model_config = ConfigDict(frozen=True)

    @field_validator("attribute_code")
    @classmethod
    def normalize_attribute_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("attribute_label")
    @classmethod
    def normalize_attribute_label(cls, value: str) -> str:
        return _clean_text(value)


class CatalogCourse(BaseModel):
    subject: str = Field(min_length=2)
    number: str = Field(min_length=1)
    title: str = Field(min_length=1)
    credits: str | None = None
    description: str | None = None
    prerequisites: str | None = None
    other_information: str | None = None
    catalog_edition: str = Field(min_length=1)
    attributes: tuple[CatalogAttribute, ...] = ()

    model_config = ConfigDict(frozen=True)

    @field_validator("subject")
    @classmethod
    def normalize_subject(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("number")
    @classmethod
    def normalize_number(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("title", "catalog_edition")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return _clean_text(value)

    @field_validator("credits", "description", "prerequisites", "other_information")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = _clean_text(value)
        return cleaned or None


_COURSE_HEADING_PATTERNS = (
    re.compile(
        r"^(?P<subject>[A-Za-z]{2,4})\s*-\s*(?P<number>\d{4}[A-Za-z]?)"
        r"\s*(?::|-)\s*(?P<title>.+)$"
    ),
    re.compile(
        r"^(?P<subject>[A-Za-z]{2,4})\s+(?P<number>\d{4}[A-Za-z]?)"
        r"\s*(?::|-)\s*(?P<title>.+)$"
    ),
    re.compile(
        r"^(?P<subject>[A-Za-z]{2,4})\s+(?P<number>\d{4}[A-Za-z]?)"
        r"\s+(?P<title>.+)$"
    ),
)
_CREDIT_TRAILER_RE = re.compile(r"\s+Credit Hours?:\s*.+$", re.IGNORECASE)
_CREDITS_RE = re.compile(
    r"(?P<credits>\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)\s*(?:credit|credits|credit hours)",
    re.IGNORECASE,
)
_CREDITS_LABEL_RE = re.compile(
    r"Credit Hours?:\s*(?P<credits>\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)",
    re.IGNORECASE,
)
_ATTRIBUTE_CODE_RE = r"[A-Z0-9]{2,10}"
_ATTRIBUTE_PREFIX_RE = re.compile(
    rf"^(?P<code>{_ATTRIBUTE_CODE_RE})\s*[-:]\s*(?P<label>.+)$",
    re.IGNORECASE,
)
_ATTRIBUTE_SUFFIX_RE = re.compile(
    rf"^(?P<label>.+?)\s*\((?P<code>{_ATTRIBUTE_CODE_RE})\)$",
    re.IGNORECASE,
)


def parse_catalog_html(html: str, catalog_edition: str) -> list[CatalogCourse]:
    soup = BeautifulSoup(html, "lxml")
    blocks = [block for block in soup.select(".courseblock") if isinstance(block, Tag)]

    if blocks:
        courses = [_parse_course_block(block, catalog_edition) for block in blocks]
    else:
        courses = [_parse_course_page(soup, catalog_edition)]

    if not courses:
        raise CatalogParseError("No course records found in catalog HTML.")
    return courses


def _parse_course_block(block: Tag, catalog_edition: str) -> CatalogCourse:
    heading_text = _first_text(block.select(".courseblocktitle, h1, h2, h3"))
    subject, number, title = _parse_course_heading(heading_text)
    block_text = _node_text(block)

    return CatalogCourse(
        subject=subject,
        number=number,
        title=title,
        credits=_extract_credits(block),
        description=_extract_courseblock_description(block),
        prerequisites=_extract_labeled_value(block, ("Prerequisite(s)", "Prerequisites")),
        other_information=_extract_labeled_value(block, ("Other Information",)),
        catalog_edition=catalog_edition,
        attributes=tuple(parse_catalog_attributes(_extract_attribute_text(block) or block_text)),
    )


def _parse_course_page(soup: BeautifulSoup, catalog_edition: str) -> CatalogCourse:
    heading_text = _find_course_heading(soup)
    subject, number, title = _parse_course_heading(heading_text)

    return CatalogCourse(
        subject=subject,
        number=number,
        title=title,
        credits=_extract_credits(soup),
        description=_extract_labeled_value(soup, ("Description",)),
        prerequisites=_extract_labeled_value(soup, ("Prerequisites", "Prerequisite(s)")),
        other_information=_extract_labeled_value(soup, ("Other Information",)),
        catalog_edition=catalog_edition,
        attributes=tuple(parse_catalog_attributes(_extract_attribute_text(soup) or "")),
    )


def parse_catalog_attributes(raw_text: str) -> list[CatalogAttribute]:
    attributes: list[CatalogAttribute] = []
    for fragment in _split_attribute_fragments(raw_text):
        parsed = _parse_attribute_fragment(fragment)
        if parsed is not None:
            attributes.append(parsed)
    return attributes


def _parse_attribute_fragment(fragment: str) -> CatalogAttribute | None:
    cleaned = _clean_text(fragment).strip(" .")
    if not cleaned:
        return None

    prefix_match = _ATTRIBUTE_PREFIX_RE.match(cleaned)
    if prefix_match is not None:
        return CatalogAttribute(
            attribute_code=prefix_match.group("code"),
            attribute_label=prefix_match.group("label"),
        )

    suffix_match = _ATTRIBUTE_SUFFIX_RE.match(cleaned)
    if suffix_match is not None:
        return CatalogAttribute(
            attribute_code=suffix_match.group("code"),
            attribute_label=suffix_match.group("label"),
        )

    return None


def _split_attribute_fragments(raw_text: str) -> list[str]:
    normalized = raw_text.replace("\xa0", " ")
    return [
        _clean_text(fragment)
        for fragment in re.split(r"[,;\n]+", normalized)
        if _clean_text(fragment)
    ]


def _parse_course_heading(text: str) -> tuple[str, str, str]:
    cleaned = _clean_text(_CREDIT_TRAILER_RE.sub("", text))
    for pattern in _COURSE_HEADING_PATTERNS:
        match = pattern.match(cleaned)
        if match is not None:
            return (
                match.group("subject").upper(),
                match.group("number").upper(),
                _clean_text(match.group("title")),
            )
    raise CatalogParseError(f"Could not parse course heading: {text!r}.")


def _find_course_heading(soup: BeautifulSoup) -> str:
    for node in soup.find_all(["h1", "h2", "h3", "strong"]):
        if not isinstance(node, Tag):
            continue
        text = _node_text(node)
        heading_without_credits = _CREDIT_TRAILER_RE.sub("", text)
        if any(pattern.match(heading_without_credits) for pattern in _COURSE_HEADING_PATTERNS):
            return text
    raise CatalogParseError("Could not find a course heading in catalog HTML.")


def _extract_credits(root: Tag | BeautifulSoup) -> str | None:
    labeled_value = _extract_labeled_value(root, ("Credit Hours", "Credits"))
    if labeled_value is not None:
        credit_match = re.search(r"\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?", labeled_value)
        return credit_match.group(0) if credit_match is not None else labeled_value

    root_text = _node_text(root)
    credit_match = _CREDITS_LABEL_RE.search(root_text)
    if credit_match is not None:
        return credit_match.group("credits")

    credit_match = _CREDITS_RE.search(root_text)
    if credit_match is None:
        return None
    return credit_match.group("credits")


def _extract_courseblock_description(block: Tag) -> str | None:
    for selector in (".courseblockdesc", ".courseblockdescription"):
        text = _first_text(block.select(selector))
        if text:
            return text
    return _extract_labeled_value(block, ("Description",))


def _extract_labeled_value(root: Tag | BeautifulSoup, labels: Iterable[str]) -> str | None:
    label_tuple = tuple(labels)

    for row in root.find_all("tr"):
        if not isinstance(row, Tag):
            continue
        cells = _direct_cell_texts(row)
        if len(cells) >= 2 and _matches_any_label(cells[0], label_tuple):
            return _clean_text(" ".join(cells[1:]))

    for label_node in root.find_all(["dt", "strong", "b"]):
        if not isinstance(label_node, Tag):
            continue
        text = _node_text(label_node)
        if not _matches_any_label(text, label_tuple):
            continue

        parent = label_node.parent if isinstance(label_node.parent, Tag) else None
        next_dd = label_node.find_next_sibling("dd")
        if isinstance(next_dd, Tag):
            return _node_text(next_dd)
        if parent is not None:
            parent_text = _node_text(parent)
            inline_value = _strip_inline_label(parent_text, label_tuple)
            if inline_value:
                return inline_value

    for node in root.find_all(["p", "div", "li"]):
        if not isinstance(node, Tag):
            continue
        inline_value = _strip_inline_label(_node_text(node), label_tuple)
        if inline_value:
            return inline_value

    return None


def _extract_attribute_text(root: Tag | BeautifulSoup) -> str | None:
    heading = _find_heading_containing(root, "course attributes")
    if heading is not None:
        fragments: list[str] = []
        for sibling in heading.next_siblings:
            if isinstance(sibling, Tag) and sibling.name in {"h1", "h2", "h3", "h4"}:
                break
            if not isinstance(sibling, Tag):
                continue
            if sibling.name == "table":
                for row in sibling.find_all("tr"):
                    if not isinstance(row, Tag):
                        continue
                    cells = _direct_cell_texts(row)
                    if len(cells) >= 2:
                        fragments.append(" ".join(cells[1:]))
                    elif cells:
                        fragments.append(cells[0])
            else:
                fragments.append(_node_text(sibling))

        text = _clean_text("\n".join(fragment for fragment in fragments if fragment))
        if text:
            return text

    return _extract_labeled_value(
        root,
        ("Course Attributes", "Course Attributes(s)", "Attribute(s)", "Attributes"),
    )


def _find_heading_containing(root: Tag | BeautifulSoup, needle: str) -> Tag | None:
    for heading in root.find_all(["h1", "h2", "h3", "h4", "strong", "b"]):
        if not isinstance(heading, Tag) or needle not in _node_text(heading).lower():
            continue
        if heading.name in {"strong", "b"} and isinstance(heading.parent, Tag):
            return heading.parent
        return heading
    return None


def _strip_inline_label(text: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        pattern = re.compile(
            rf"^{re.escape(label)}(?:\s*:\s*|\s+)(?P<value>.+)$",
            re.IGNORECASE,
        )
        match = pattern.match(text)
        if match is not None:
            return _clean_text(match.group("value"))
    return None


def _matches_any_label(text: str, labels: tuple[str, ...]) -> bool:
    normalized = _normalize_label(text)
    return any(normalized == _normalize_label(label) for label in labels)


def _normalize_label(text: str) -> str:
    return _clean_text(text).lower().rstrip(":").replace("(s)", "s")


def _first_text(nodes: Iterable[Tag]) -> str:
    for node in nodes:
        text = _node_text(node)
        if text:
            return text
    return ""


def _direct_cell_texts(row: Tag) -> list[str]:
    return [
        _node_text(cell)
        for cell in row.find_all(["th", "td"], recursive=False)
        if isinstance(cell, Tag)
    ]


def _node_text(node: Tag | BeautifulSoup) -> str:
    return _clean_text(node.get_text(" ", strip=True))


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()
