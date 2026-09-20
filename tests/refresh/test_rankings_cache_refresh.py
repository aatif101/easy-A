from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.db import Base
from easy_a.models import Course, GradeDistribution
from easy_a.rankings.cache import SectionRankingCache, hydrate_ranking
from easy_a.rankings.service import rank_section
from easy_a.refresh import RefreshConfig, RefreshStageError, ScheduleInput, SourceMode, refresh_data
from easy_a.refresh.coverage import refresh_targets
from easy_a.refresh.targets import load_targets
from tests.refresh.test_targets import NOW, schedule

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_refresh_targets_populates_and_updates_rankings_cache(db_session: Session) -> None:
    config = load_targets()

    refresh_targets(
        db_session,
        term="202701",
        config=config,
        subject="MAC",
        course="1105",
        search=schedule,
        observed_at=NOW,
    )

    cached = db_session.scalars(
        select(SectionRankingCache).order_by(SectionRankingCache.crn)
    ).all()
    assert [row.crn for row in cached] == ["13173", "19410"]
    original_score = cached[0].easiness_score
    assert cached[0].effective_n == 0

    db_session.add(
        GradeDistribution(
            term_id=2,
            crn="89033",
            course_id=10,
            section_number_raw="001",
            section_suffix_raw="C",
            campus_raw="Tampa",
            a_count=100,
            b_count=0,
            c_count=0,
            d_count=0,
            f_count=0,
            i_count=0,
            s_count=0,
            u_count=0,
            w_count=0,
            other_count=0,
            total_grades=100,
            source="rankings-cache-refresh",
            source_hash="rankings-cache-refresh",
        )
    )
    refresh_targets(
        db_session,
        term="202701",
        config=config,
        subject="MAC",
        course="1105",
        search=schedule,
        observed_at=datetime(2026, 9, 8, 0, 1, tzinfo=UTC),
    )

    db_session.expire_all()
    refreshed = db_session.scalar(
        select(SectionRankingCache).where(SectionRankingCache.crn == "13173")
    )
    assert refreshed is not None
    assert refreshed.effective_n > 0
    assert refreshed.easiness_score != original_score
    as_of = datetime(2026, 9, 8, 1, tzinfo=UTC)
    assert hydrate_ranking(db_session, refreshed, as_of=as_of).model_dump(
        mode="json"
    ) == rank_section(
        db_session,
        term="202701",
        crn="13173",
        as_of=as_of,
    ).model_dump(mode="json")


def test_refresh_data_populates_rankings_for_a_fresh_term(tmp_path: Path) -> None:
    factory = _factory_with_mac_course()
    schedule_path = tmp_path / "schedule.html"
    schedule_path.write_text(
        (FIXTURES / "schedule_current.html").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = refresh_data(
        RefreshConfig(
            term="202701",
            schedule=ScheduleInput(source=SourceMode.file, file_path=schedule_path),
        ),
        session_factory=factory,
        observed_at=NOW,
        quality_as_of=NOW,
    )

    assert result.sections == 2
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(SectionRankingCache)) == 2


def test_refresh_data_wraps_rankings_cache_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = _factory_with_mac_course()

    def fail_cache_refresh(*args: object, **kwargs: object) -> int:
        raise RuntimeError("cache unavailable")

    monkeypatch.setattr(
        "easy_a.refresh.service.refresh_section_rankings",
        fail_cache_refresh,
        raising=False,
    )

    with pytest.raises(RefreshStageError, match="rankings cache stage failed: cache unavailable"):
        refresh_data(RefreshConfig(term="202701"), session_factory=factory)


def _factory_with_mac_course() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
        session.add(
            Course(
                subject="MAC",
                number="1105",
                title="College Algebra",
                catalog_edition="2026-2027",
            )
        )
    return factory
