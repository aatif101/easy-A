"""Build web/src/data/rmp-profiles.json: (subject, instructor) -> Rate My Professors profile id.

Reads every usable (instructor name, course subject) pair from ``section_instructors`` inside one
read-only transaction, looks up each distinct last name once on RMP (sequential, rate-limited,
cached under ``.cache/rmp/``), and keeps a profile only when it is unambiguous
(``easy_a.rmp.matcher``). Unmatched instructors get a last-name search link in the UI instead.

Owner corrections live in ``src/easy_a/rmp/overrides.json`` as ``{"ENC|n. volz": 3028196}``;
``null`` blocks a wrong auto-match. Overrides always win.

Only profile ids are written (PROJECT.md D-08 as amended 2026-10-07). Rerun when a new term
brings new instructors; ``--offline`` rebuilds from the cache without touching RMP.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from easy_a.common.instructors import is_usable_instructor
from easy_a.db import get_engine
from easy_a.models import Course, Section, SectionInstructor
from easy_a.rmp.client import RmpSearchClient
from easy_a.rmp.matcher import Match, apply_overrides, link_key, match_teacher, parse_name

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "web" / "src" / "data" / "rmp-profiles.json"
OVERRIDES = ROOT / "src" / "easy_a" / "rmp" / "overrides.json"
CACHE_DIR = ROOT / ".cache" / "rmp"


def load_pairs(session: Session) -> dict[str, set[str]]:
    """Cleaned instructor name -> every subject that name taught at USF. Issues no writes."""
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
    rows = session.execute(
        select(SectionInstructor.name_raw, Course.subject)
        .join(Section, Section.id == SectionInstructor.section_id)
        .join(Course, Course.id == Section.course_id)
        .distinct()
    )
    subjects_by_name: dict[str, set[str]] = defaultdict(set)
    for name_raw, subject in rows:
        name = " ".join(name_raw.split())
        if is_usable_instructor(name):
            subjects_by_name[name].add(subject.strip().upper())
    return subjects_by_name


def build_links(
    subjects_by_name: dict[str, set[str]],
    client: RmpSearchClient,
    overrides: dict[str, int | None],
) -> tuple[dict[str, int], Counter[str]]:
    matches: dict[str, Match | None] = {}
    stats: Counter[str] = Counter()
    for name in sorted(subjects_by_name):
        parsed = parse_name(name)
        teachers = client.search(parsed.search_text) if parsed else None
        for subject in sorted(subjects_by_name[name]):
            stats["pairs"] += 1
            if teachers is None:
                stats["not_looked_up"] += 1
                continue
            matches[link_key(subject, name)] = match_teacher(
                name, subject, teachers, name_subjects=subjects_by_name[name]
            )
    merged = apply_overrides(matches, overrides)
    links: dict[str, int] = {}
    for key, found in sorted(merged.items()):
        stats[found.method.value if found else "no_match"] += 1
        if found:
            links[key] = found.legacy_id
    stats["instructors"] = len(subjects_by_name)
    stats["rmp_requests"] = client.requests_made
    return links, stats


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="Use only cached RMP responses.")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between RMP requests.")
    args = parser.parse_args(argv)

    engine = get_engine()
    try:
        with Session(engine) as session:
            subjects_by_name = load_pairs(session)
    finally:
        engine.dispose()

    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    client = RmpSearchClient(CACHE_DIR, delay_seconds=args.delay, offline=args.offline)
    links, stats = build_links(subjects_by_name, client, overrides)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(links, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(dict(stats), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
