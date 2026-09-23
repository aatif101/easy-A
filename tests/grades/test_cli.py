from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from easy_a.db import Base
from easy_a.grades import cli
from easy_a.models import IngestRun


def test_failed_grade_import_rolls_back_partial_database_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'grades.db'}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(cli, "get_session_factory", lambda: sessionmaker(bind=engine))

    def fail_after_partial_write(session: Session, **_kwargs: object) -> None:
        session.add(IngestRun(source="test", status="running"))
        session.flush()
        raise RuntimeError("import failed after writing")

    monkeypatch.setattr(cli, "ingest_grade_file", fail_after_partial_write)

    with pytest.raises(RuntimeError, match="import failed after writing"):
        cli.main(["--term", "202601", "--file", str(tmp_path / "unused.xlsx")])

    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(IngestRun)) == 0
