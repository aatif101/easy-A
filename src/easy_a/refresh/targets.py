from __future__ import annotations

import tomllib
from pathlib import Path
from string import Formatter

from pydantic import BaseModel, ConfigDict, Field, model_validator

from easy_a.config import get_settings


class CourseTarget(BaseModel):
    subject: str = Field(pattern=r"^[A-Z]{2,4}$")
    number: str = Field(pattern=r"^[0-9]{4}[A-Z]?$")
    model_config = ConfigDict(frozen=True, extra="forbid")


class CourseTargets(BaseModel):
    catalog_edition: str = Field(min_length=1)
    catalog_url_template: str
    targets: tuple[CourseTarget, ...] = Field(min_length=1)
    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_targets(self) -> CourseTargets:
        if len(set(self.targets)) != len(self.targets):
            raise ValueError("Duplicate course targets.")
        if not self.catalog_url_template.startswith("https://"):
            raise ValueError("Catalog URL must use HTTPS.")
        fields = {
            field
            for _, field, _, _ in Formatter().parse(self.catalog_url_template)
            if field is not None
        }
        if fields != {"subject", "number"}:
            raise ValueError("Catalog URL template requires {subject} and {number} only.")
        self.catalog_url_template.format(
            subject=self.targets[0].subject, number=self.targets[0].number
        )
        return self

    def select(
        self, subject: str | None = None, course: str | None = None
    ) -> tuple[CourseTarget, ...]:
        if course and not subject:
            raise ValueError("--course requires --subject.")
        result = tuple(
            t
            for t in self.targets
            if (not subject or t.subject == subject.strip().upper())
            and (not course or t.number == course.strip().upper())
        )
        if not result:
            raise ValueError("No configured targets match the filter.")
        return result


def load_targets(path: Path | None = None) -> CourseTargets:
    source = path or Path(get_settings().course_targets_path)
    return CourseTargets.model_validate(tomllib.loads(source.read_text(encoding="utf-8")))
