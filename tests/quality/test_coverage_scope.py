from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from easy_a.quality.checks import run_quality_checks
from easy_a.refresh.targets import CourseTarget
from easy_a.schedule.client import ScheduleSearchQuery
from easy_a.schedule.ingest import ingest_schedule_html
from tests.refresh.test_targets import NOW, schedule


@pytest.mark.parametrize("term", ["202408", "202501", "202508"])
@pytest.mark.parametrize("explicit", [False, True], ids=["generic", "explicit-targets"])
def test_historical_quality_coverage_is_opt_in(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    term: str,
    explicit: bool,
) -> None:
    ingest_schedule_html(
        db_session,
        schedule(ScheduleSearchQuery(term=term, subject="MAC")),
        term,
        observed_at=NOW - timedelta(days=365),
    )
    # Generic quality must also work without a default target configuration on disk.
    monkeypatch.chdir(tmp_path)
    targets = (CourseTarget(subject="PSY", number="2012"),) if explicit else None
    report = run_quality_checks(db_session, term, as_of=NOW, targets=targets)
    checks = {finding.check_id for finding in report.findings}
    added_checks = {"target_missing_catalog", "target_missing_sections", "stale_seat_observation"}
    if explicit:
        assert added_checks <= checks
        assert all(f.severity == "warning" for f in report.findings if f.check_id in added_checks)
    else:
        assert checks.isdisjoint(added_checks)
        # Omitting targets has exactly the same opt-out behavior as passing None.
        assert run_quality_checks(db_session, term, as_of=NOW) == report
