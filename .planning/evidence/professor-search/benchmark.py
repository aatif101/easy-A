"""Synthetic before/after discovery benchmark; never connects to the hosted database.

Run: uv run --python 3.12 --locked python .planning/evidence/professor-search/benchmark.py
The baseline is pinned to main at 131ec20; results measure Python + SQLite, not network latency.
"""

from __future__ import annotations

import json
import math
import statistics
import subprocess
import sys
import time
import types
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session

from easy_a.api.routes.discovery import discover
from easy_a.db import Base
from easy_a.models import Course, Section, SectionInstructor, Term

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = "131ec209ae6030dabc8e635e148d2a12654074c6"
SAMPLES = 30
WARMUPS = 3
NOW = datetime(2026, 10, 29, tzinfo=UTC)


def seed(session: Session) -> None:
    session.execute(
        insert(Term),
        [
            {
                "id": 1,
                "banner_code": "202701",
                "name": "Spring 2027",
                "year": 2027,
                "season": "Spring",
            },
            {
                "id": 2,
                "banner_code": "202601",
                "name": "Spring 2026",
                "year": 2026,
                "season": "Spring",
            },
        ],
    )
    session.execute(
        insert(Course),
        [
            {
                "id": i + 1,
                "subject": "SYN",
                "number": str(1000 + i),
                "title": f"Synthetic Course {i}",
                "catalog_edition": "Synthetic benchmark",
            }
            for i in range(1400)
        ],
    )
    session.execute(
        insert(Section),
        [
            {
                "id": i + 1,
                "term_id": 1 if i < 3782 else 2,
                "course_id": i % 1400 + 1,
                "crn": str(10000 + i),
                "section_number": "001",
                "campus": "Tampa",
                "session": "Regular",
                "section_type": "Lecture",
                "primary_status": "Active",
                "first_seen_at": NOW,
                "last_seen_at": NOW,
            }
            for i in range(3782 + 8600)
        ],
    )
    session.execute(
        insert(SectionInstructor),
        [
            {
                "section_id": i + 1,
                "name_raw": (
                    "J. Smith"
                    if i % 100 == 0
                    else "A. Smithson"
                    if i % 100 == 1
                    else f"Synthetic Instructor {i % 300}"
                ),
                "source": "synthetic_benchmark",
                "observed_at": NOW,
            }
            for i in range(3782 + 8600)
        ],
    )
    session.commit()


def summary(samples: list[float]) -> dict[str, float]:
    return {
        "p50_ms": round(statistics.median(samples), 2),
        "p95_ms": round(sorted(samples)[math.ceil(len(samples) * 0.95) - 1], 2),
        "max_ms": round(max(samples), 2),
    }


def main() -> None:
    baseline = types.ModuleType("professor_search_baseline")
    sys.modules[baseline.__name__] = baseline
    source = subprocess.check_output(
        ["git", "show", f"{BASE}:src/easy_a/api/routes/discovery.py"],
        cwd=ROOT,
    ).decode("utf-8")
    exec(compile(source, "baseline_discovery.py", "exec"), baseline.__dict__)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    results = {}
    with Session(engine) as session:
        seed(session)
        for query in ("smith", "j smith", "smi", "no such name"):
            measurements: dict[str, list[float]] = {"before": [], "after": []}
            for iteration in range(WARMUPS + SAMPLES):
                variants = [("before", baseline.discover), ("after", discover)]
                if iteration % 2:
                    variants.reverse()
                for label, function in variants:
                    start = time.perf_counter()
                    function(term="202701", session=session, q=query, limit=20, offset=0)
                    elapsed = (time.perf_counter() - start) * 1000
                    if iteration >= WARMUPS:
                        measurements[label].append(elapsed)
            results[query] = {label: summary(values) for label, values in measurements.items()}
            print(query, results[query], flush=True)
    output = {
        "environment": (
            f"Python {sys.version.split()[0]}; Windows; "
            "direct endpoint calls + SQLite; synthetic only"
        ),
        "baseline_sha": BASE,
        "generated_courses": 1400,
        "generated_current_sections": 3782,
        "generated_historical_sections": 8600,
        "warmups_per_query": WARMUPS,
        "samples_per_query": SAMPLES,
        "ordering": "alternating before/after; response cache bypassed",
        "scope": (
            "Discovery query cost only; excludes HTTP, network, "
            "hosted PostgreSQL and browser rendering"
        ),
        "results": results,
    }
    (HERE / "performance.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    engine.dispose()


if __name__ == "__main__":
    main()
