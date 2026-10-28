"""GradeEvidenceCache must return exactly what a fresh read would, and reload on any change."""

from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.orm import Session

from easy_a.analytics.queries import (
    GradeEvidenceCache,
    _TermGradeEvidence,
    get_term_section_historical_analytics,
)
from easy_a.models import GradeDistribution
from tests.analytics.test_queries import (
    BREAKDOWN_COURSE_KEYS,
    _add_grade,
    _add_section,
    seed_breakdown_branches,
)


def test_cached_evidence_gives_identical_analytics_and_is_read_once(db_session: Session) -> None:
    seed_breakdown_branches(db_session)
    cache = GradeEvidenceCache()

    fresh = get_term_section_historical_analytics(
        db_session, term_code="202701", course_keys=BREAKDOWN_COURSE_KEYS
    )
    first = get_term_section_historical_analytics(
        db_session, term_code="202701", course_keys=BREAKDOWN_COURSE_KEYS, evidence_cache=cache
    )
    second = get_term_section_historical_analytics(
        db_session, term_code="202701", course_keys=BREAKDOWN_COURSE_KEYS, evidence_cache=cache
    )

    assert first == fresh
    assert second == fresh
    assert cache.loads == 1


def test_new_grades_instructors_or_reattribution_reload_the_evidence(db_session: Session) -> None:
    seed_breakdown_branches(db_session)
    cache = GradeEvidenceCache()
    cache.get(db_session, before_term_code="202701")

    _add_grade(db_session, term_id=2, crn="61009", a=5, b=5)
    db_session.commit()
    assert cache.get(db_session, before_term_code="202701") == _TermGradeEvidence.load(
        db_session, before_term_code="202701"
    )
    assert cache.loads == 2

    _add_section(db_session, term_id=2, crn="61009", instructor="P. Prime")
    db_session.commit()
    cache.get(db_session, before_term_code="202701")
    assert cache.loads == 3

    db_session.execute(
        update(GradeDistribution).where(GradeDistribution.crn == "61009").values(course_id=11)
    )
    db_session.commit()
    cache.get(db_session, before_term_code="202701")
    assert cache.loads == 4

    # A current-term write (what a sweep does) leaves the pre-term evidence alone.
    _add_section(db_session, term_id=1, crn="71099", instructor="N. Newcomer")
    db_session.commit()
    cache.get(db_session, before_term_code="202701")
    assert cache.loads == 4
