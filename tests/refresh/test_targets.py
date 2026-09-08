from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.models import GradeDistribution, SeatSnapshot, Section
from easy_a.quality.checks import run_quality_checks
from easy_a.rankings import rank_section
from easy_a.refresh.coverage import coverage_metadata, refresh_targets
from easy_a.refresh.targets import CourseTarget, load_targets
from easy_a.schedule.client import ScheduleSearchQuery
from easy_a.schedule.freshness import classify_observation, snapshot_freshness
from tests.rankings.test_service import _add_grade, _add_syllabus

NOW = datetime(2026, 9, 8, tzinfo=UTC)
FIXTURES = Path(__file__).parents[1] / "fixtures"


def schedule(query: ScheduleSearchQuery) -> str:
    html = (FIXTURES / "schedule_current.html").read_text(encoding="utf-8")
    if query.subject == "ENC":
        html = html.replace("MAC", "ENC").replace("1105", "1101")
        html = html.replace("13173", "23173").replace("19410", "29410")
    if query.crn:
        soup = BeautifulSoup(html, "lxml")
        for row in soup.select("tr"):
            cells = row.find_all("td")
            if cells and cells[3].get_text() != query.crn:
                row.decompose()
        return str(soup)
    return html


def test_config_parsing_and_filters(tmp_path: Path) -> None:
    config = load_targets()
    assert len(config.targets) == 5
    assert config.select("mac", "1105") == (CourseTarget(subject="MAC", number="1105"),)
    for subject, course in [(None, "1105"), ("XXX", None)]:
        with pytest.raises(ValueError):
            config.select(subject, course)
    source = Path("config/course_targets.toml").read_text()
    path = tmp_path / "targets.toml"
    path.write_text(source + '\n[[targets]]\nsubject="MAC"\nnumber="1105"\n')
    with pytest.raises(ValueError, match="Duplicate"):
        load_targets(path)
    path.write_text(source.replace('subject = "MAC"', 'subject = "../MAC"'))
    with pytest.raises(ValueError):
        load_targets(path)


def test_multiple_coverage_refresh_and_missing(db_session: Session) -> None:
    config = load_targets()
    queried = []

    def search(query: ScheduleSearchQuery) -> str:
        queried.append(query.subject)
        return schedule(query)

    rows = refresh_targets(db_session, term="202701", config=config, search=search, observed_at=NOW)
    assert [r.section_count for r in rows] == [2, 2, 0, 0, 0]
    assert queried == ["MAC", "ENC"]
    report = run_quality_checks(db_session, "202701", as_of=NOW, targets=config.targets)
    assert sum(f.check_id == "target_missing_catalog" for f in report.findings) == 3
    assert sum(f.check_id == "target_missing_sections" for f in report.findings) == 3
    metadata = coverage_metadata(db_session, "202701", config.targets)
    assert [r.section_count for r in metadata] == [2, 2, 0, 0, 0]


def test_catalog_refresh_creates_required_metadata(db_session: Session) -> None:
    config = load_targets()

    def catalog(url: str) -> str:
        assert "/prefix/PSY/code/2012" in url
        return "<h1>PSY 2012: Introduction to Psychology</h1>"

    rows = refresh_targets(
        db_session,
        term="202701",
        config=config,
        subject="PSY",
        refresh_catalog=True,
        catalog_fetch=catalog,
        search=lambda _: (FIXTURES / "schedule_not_found.html").read_text(),
        observed_at=NOW,
    )
    assert rows[0].catalog_present
    assert rows[0].section_count == 0


def test_seats_append_preserve_identity_grades_syllabus_and_score(db_session: Session) -> None:
    config = load_targets()
    _add_grade(db_session, term_id=2, crn="89033", a=40, b=20, w=5)
    syllabus = _add_syllabus(
        db_session,
        document_id="test",
        term_id=1,
        crn="13173",
        instructor="Staff",
        text="Unchanged syllabus",
    )
    refresh_targets(
        db_session, term="202701", config=config, search=schedule, subject="MAC", observed_at=NOW
    )
    before = rank_section(db_session, term="202701", crn="13173")
    identities = list(db_session.execute(select(Section.id, Section.term_id, Section.crn)))
    grades = [
        tuple(getattr(g, c.name) for c in GradeDistribution.__table__.columns)
        for g in db_session.scalars(select(GradeDistribution))
    ]

    def updated(query: ScheduleSearchQuery) -> str:
        return schedule(query).replace("<td>135</td><td>0</td>", "<td>135</td><td>1</td>")

    rows = refresh_targets(
        db_session,
        term="202701",
        config=config,
        search=updated,
        subject="MAC",
        course="1105",
        observed_at=NOW + timedelta(minutes=1),
    )
    after = rank_section(db_session, term="202701", crn="13173")
    assert sum(r.snapshots_added for r in rows) == 2
    assert len(list(db_session.scalars(select(SeatSnapshot)))) == 4
    assert identities == list(db_session.execute(select(Section.id, Section.term_id, Section.crn)))
    assert grades == [
        tuple(getattr(g, c.name) for c in GradeDistribution.__table__.columns)
        for g in db_session.scalars(select(GradeDistribution))
    ]
    db_session.refresh(syllabus)
    assert syllabus.content_text == "Unchanged syllabus"
    assert before.historical_analytics == after.historical_analytics
    assert before.seats.enrollment != after.seats.enrollment
    report = run_quality_checks(
        db_session, "202701", as_of=NOW + timedelta(hours=1), targets=config.targets
    )
    assert any(
        f.check_id == "stale_seat_observation" and f.severity == "warning" for f in report.findings
    )
    assert rank_section(db_session, term="202701", crn="13173").historical_analytics == (
        before.historical_analytics
    )


def test_crn_refresh_and_scope_rejection(db_session: Session) -> None:
    config = load_targets()
    refresh_targets(
        db_session, term="202701", config=config, search=schedule, subject="MAC", observed_at=NOW
    )
    rows = refresh_targets(
        db_session,
        term="202701",
        config=config,
        search=schedule,
        crn="13173",
        observed_at=NOW + timedelta(minutes=1),
    )
    assert rows[0].snapshots_added == 1
    assert len(list(db_session.scalars(select(SeatSnapshot)))) == 3
    for crn in ["99999", "bad"]:
        with pytest.raises(ValueError):
            refresh_targets(db_session, term="202701", config=config, search=schedule, crn=crn)
    with pytest.raises(ValueError, match="scope"):
        refresh_targets(
            db_session,
            term="202701",
            config=config,
            subject="ENC",
            search=lambda _: schedule(ScheduleSearchQuery(term="202701", subject="MAC")),
        )


def test_empty_pass_does_not_report_old_sections_as_refreshed(db_session: Session) -> None:
    config = load_targets()
    refresh_targets(db_session, term="202701", config=config, search=schedule, subject="MAC")
    rows = refresh_targets(
        db_session,
        term="202701",
        config=config,
        subject="MAC",
        search=lambda _: (FIXTURES / "schedule_not_found.html").read_text(),
    )
    assert rows[0].section_count == 0
    assert len(list(db_session.scalars(select(Section)))) == 2


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "fresh"),
        (600, "fresh"),
        (601, "aging"),
        (1800, "aging"),
        (1801, "stale"),
        (-1, "unavailable"),
    ],
)
def test_freshness_boundaries(seconds: int, expected: str) -> None:
    result = classify_observation(NOW - timedelta(seconds=seconds), as_of=NOW)
    assert result.freshness == expected
    assert result.age_seconds == (seconds if seconds >= 0 else None)


def test_unavailable_and_custom_thresholds() -> None:
    assert classify_observation(None).freshness == "unavailable"
    assert snapshot_freshness(None).freshness == "unavailable"
    assert snapshot_freshness(SeatSnapshot(observed_at=NOW)).freshness == "unavailable"
    assert classify_observation(NOW.replace(tzinfo=None), as_of=NOW).age_seconds == 0
    assert (
        classify_observation(
            NOW, as_of=NOW + timedelta(seconds=11), fresh_seconds=5, stale_seconds=10
        ).freshness
        == "stale"
    )
    with pytest.raises(ValueError):
        classify_observation(NOW, fresh_seconds=20, stale_seconds=10)


def test_multiple_catalog_targets(db_session: Session) -> None:
    config = load_targets().model_copy(update={"targets": load_targets().targets[:2]})
    urls = []

    def catalog(url: str) -> str:
        urls.append(url)
        if "/MAC/" in url:
            return "<h1>MAC 1105: Updated Algebra</h1>"
        return "<h1>ENC 1101: Updated Composition</h1>"

    rows = refresh_targets(
        db_session,
        term="202701",
        config=config,
        search=schedule,
        catalog_fetch=catalog,
        refresh_catalog=True,
    )
    assert len(urls) == 2
    assert [r.section_count for r in rows] == [2, 2]


def test_cli_one_pass_and_empty_warning(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from sqlalchemy.orm import sessionmaker

    from easy_a.refresh.target_cli import main

    calls = []

    def search(self: object, query: ScheduleSearchQuery) -> str:
        calls.append(query)
        return schedule(query)

    monkeypatch.setattr(
        "easy_a.refresh.target_cli.get_session_factory",
        lambda: sessionmaker(bind=db_session.get_bind()),
    )
    monkeypatch.setattr("easy_a.schedule.client.StaffScheduleClient.search", search)
    assert main(["--term", "202701", "--subject", "MAC", "--course", "1105"]) == 0
    assert len(calls) == 1
    assert "Sections: 2" in capsys.readouterr().out
    monkeypatch.setattr(
        "easy_a.schedule.client.StaffScheduleClient.search",
        lambda self, query: (FIXTURES / "schedule_not_found.html").read_text(),
    )
    assert main(["--term", "202701", "--subject", "MAC"]) == 0
    output = capsys.readouterr().out
    assert "Missing targets: 1" in output
    assert "target_missing_refresh" in output


def test_cli_source_failure_rolls_back(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy.orm import sessionmaker

    from easy_a.refresh.target_cli import main

    def search(self: object, query: ScheduleSearchQuery) -> str:
        if query.subject == "ENC":
            raise RuntimeError("source failed")
        return schedule(query)

    monkeypatch.setattr(
        "easy_a.refresh.target_cli.get_session_factory",
        lambda: sessionmaker(bind=db_session.get_bind()),
    )
    monkeypatch.setattr("easy_a.schedule.client.StaffScheduleClient.search", search)
    with pytest.raises(RuntimeError, match="source failed"):
        main(["--term", "202701"])
    assert not list(db_session.scalars(select(SeatSnapshot)))
    assert not list(db_session.scalars(select(Section)))


@pytest.mark.parametrize("coverage", [True, False], ids=["coverage", "seats"])
def test_refresh_cli_explicit_quality_scope(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    coverage: bool,
) -> None:
    from functools import partial

    from sqlalchemy.orm import sessionmaker

    from easy_a.refresh.target_cli import main

    config = load_targets()
    refresh_targets(
        db_session,
        term="202701",
        config=config,
        search=schedule,
        subject="MAC",
        observed_at=NOW - timedelta(days=365),
    )
    db_session.commit()
    monkeypatch.setattr(
        "easy_a.refresh.target_cli.get_session_factory",
        lambda: sessionmaker(bind=db_session.get_bind()),
    )
    # A valid empty response preserves old observations, so stale-seat warnings still apply.
    monkeypatch.setattr(
        "easy_a.schedule.client.StaffScheduleClient.search",
        lambda self, query: (FIXTURES / "schedule_not_found.html").read_text(),
    )

    def catalog(url: str) -> str:
        parts = url.split("/")
        return f"<h1>{parts[-3]} {parts[-1]}: Synthetic course</h1>"

    monkeypatch.setattr(
        "easy_a.refresh.target_cli.refresh_targets", partial(refresh_targets, catalog_fetch=catalog)
    )
    assert main(["--term", "202701"], coverage=coverage) == 0
    output = capsys.readouterr().out
    assert "Missing targets: 5" in output
    assert "warning: target_missing_sections:" in output
    assert "warning: stale_seat_observation:" in output
