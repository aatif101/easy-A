from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class FindingSeverity(StrEnum):
    error = "error"
    warning = "warning"
    info = "info"


class QualityFinding(BaseModel):
    check_id: str
    severity: FindingSeverity
    message: str
    term: str | None = None
    crn: str | None = None
    source_record: str | None = None

    model_config = ConfigDict(frozen=True)


class QualityReport(BaseModel):
    term: str
    generated_at: datetime
    section_count: int
    error_count: int
    warning_count: int
    info_count: int
    findings: tuple[QualityFinding, ...]

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_findings(
        cls,
        *,
        term: str,
        generated_at: datetime,
        section_count: int,
        findings: list[QualityFinding],
    ) -> QualityReport:
        ordered = tuple(
            sorted(
                findings,
                key=lambda finding: (
                    _SEVERITY_ORDER[finding.severity],
                    finding.check_id,
                    finding.crn or "",
                    finding.source_record or "",
                ),
            )
        )
        return cls(
            term=term,
            generated_at=generated_at,
            section_count=section_count,
            error_count=sum(
                finding.severity is FindingSeverity.error for finding in ordered
            ),
            warning_count=sum(
                finding.severity is FindingSeverity.warning for finding in ordered
            ),
            info_count=sum(finding.severity is FindingSeverity.info for finding in ordered),
            findings=ordered,
        )

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0


_SEVERITY_ORDER = {
    FindingSeverity.error: 0,
    FindingSeverity.warning: 1,
    FindingSeverity.info: 2,
}
