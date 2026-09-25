"""Read-only, bounded sketch snapshot. Run from repo root with .venv/bin/python.

Stores course aggregates and public schedule facts, never raw grade export rows.
Requires the existing DATABASE_URL and local API at 127.0.0.1:8000.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from sqlalchemy import text

from easy_a.db import get_engine

ROOT = Path(__file__).parent
COURSES = [
    ("MAC", "1105"),
    ("ENC", "1101"),
    ("PSY", "2012"),
    ("BSC", "1005"),
    ("AMH", "2020"),
    ("MVJ", "1111"),
    ("CAI", "1000"),
    ("THE", "3111"),
]
BUCKETS = ["a", "b", "c", "d", "f", "i", "s", "u", "w", "other"]


def main():
    snapshot = {
        "captured_at": datetime.now(UTC).isoformat(),
        "term": "202701",
        "source": "USF InfoCenter",
        "scope": "Eight selected courses; not the full catalog",
        "courses": [],
    }
    with get_engine().connect() as conn:
        conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        for subject, number in COURSES:
            params = {"subject": subject, "number": number}
            select_counts = ", ".join(f"COALESCE(SUM(g.{b}_count),0) AS {b}" for b in BUCKETS)
            aggregate = dict(
                conn.execute(
                    text(f"""
                SELECT {select_counts}, COALESCE(SUM(g.total_grades),0) AS total,
                  COUNT(DISTINCT (g.term_id,g.crn)) FILTER(WHERE g.id IS NOT NULL) AS section_count,
                  MIN(t.banner_code) AS first_term, MAX(t.banner_code) AS last_term,
                  MAX(g.ingested_at) AS ingested_at,
                  ARRAY_AGG(DISTINCT g.source) FILTER(WHERE g.source IS NOT NULL) AS sources,
                  ARRAY_AGG(DISTINCT g.source_hash)
                    FILTER(WHERE g.source_hash IS NOT NULL) AS source_hashes
                FROM courses c LEFT JOIN grade_distributions g ON g.course_id=c.id
                  AND g.term_id IN (SELECT id FROM terms WHERE banner_code < '202701')
                LEFT JOIN terms t ON t.id=g.term_id
                WHERE c.subject=:subject AND c.number=:number
            """),
                    params,
                )
                .mappings()
                .one()
            )
            duplicate_sources = conn.execute(
                text("""
                SELECT COUNT(*) FROM (
                  SELECT g.term_id,g.crn FROM grade_distributions g
                  JOIN courses c ON c.id=g.course_id
                  JOIN terms t ON t.id=g.term_id WHERE c.subject=:subject AND c.number=:number
                  AND t.banner_code < '202701' GROUP BY g.term_id,g.crn HAVING COUNT(*)>1
                ) d
            """),
                params,
            ).scalar_one()
            assert duplicate_sources == 0, "Resolve overlapping sources before summing"
            query = urlencode(
                {
                    "term": "202701",
                    "subject": subject,
                    "course_number": number,
                    "limit": 100,
                    "offset": 0,
                }
            )
            with urlopen("http://127.0.0.1:8000/api/v1/rankings/search?" + query, timeout=30) as r:
                page = json.load(r)
            assert len(page["items"]) == page["total"] > 0, "Incomplete course section snapshot"
            item = page["items"][0]
            n = sum(aggregate[b] for b in BUCKETS[:5])
            if n:
                assert item["score_source"] == "course", "Need separate course analytics"
                assert n == item["historical_analytics"]["completed_grade_count"]
                assert aggregate["total"] == item["historical_analytics"]["total_grade_count"]
                assert aggregate["section_count"] == item["historical_analytics"]["section_count"]
            assert sum(aggregate[b] for b in BUCKETS) == aggregate["total"]
            schedule = (
                conn.execute(
                    text("""
                SELECT s.crn, s.section_number, s.last_seen_at FROM sections s
                JOIN courses c ON c.id=s.course_id JOIN terms t ON t.id=s.term_id
                WHERE c.subject=:subject AND c.number=:number AND t.banner_code='202701'
            """),
                    params,
                )
                .mappings()
                .all()
            )
            by_crn = {row["crn"]: row for row in schedule}
            assert set(by_crn) == {s["crn"] for s in page["items"]}
            sections = [
                {
                    k: s[k]
                    for k in [
                        "crn",
                        "instructor",
                        "modality",
                        "seats",
                        "signals",
                        "signal_provenance",
                    ]
                }
                | {
                    "section_number": by_crn[s["crn"]]["section_number"],
                    "schedule_observed_at": by_crn[s["crn"]]["last_seen_at"],
                }
                for s in page["items"]
            ]
            snapshot["courses"].append(
                {
                    "code": subject + " " + number,
                    "title": item["course_title"],
                    "level": int(number[0]) * 1000,
                    "grades": aggregate,
                    "letter_count": n,
                    "score": item["easiness_score"] if n else None,
                    "confidence": item["confidence_label"] if n else None,
                    "attributes": item["gened_attributes"],
                    "sections": sections,
                    "fallback_source": item["score_source"] if not n else None,
                }
            )
    data = json.dumps(snapshot, indent=2, default=str)
    (ROOT / "snapshot.json").write_text(data + "\n")
    (ROOT / "snapshot.js").write_text("window.SKETCH_DATA = " + data + ";\n")
    for course in snapshot["courses"]:
        print(
            course["code"],
            course["grades"]["a"],
            "/",
            course["letter_count"],
            "sections",
            len(course["sections"]),
            "score",
            course["score"],
        )


if __name__ == "__main__":
    main()
