from __future__ import annotations

import argparse
import csv
from pathlib import Path

from easy_a.refresh.targets import CourseTarget, CourseTargets

DEFAULT_CSV = Path("courses.csv")
DEFAULT_OUT = Path("config/course_targets.toml")
DEFAULT_CATALOG_EDITION = "2026-2027"
CATALOG_URL_TEMPLATE = "https://cloud.usf.edu/academic-programs/details/prefix/{subject}/code/{number}"


def parse_csv_targets(csv_path: Path) -> tuple[CourseTarget, ...]:
    """Read one CourseTarget per courses.csv row, letting validation errors propagate."""
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return tuple(
            CourseTarget(subject=row["subject"], number=row["number"]) for row in reader
        )


def build_targets(
    csv_path: Path,
    *,
    catalog_edition: str = DEFAULT_CATALOG_EDITION,
) -> CourseTargets:
    """Build and validate the full CourseTargets config from a courses.csv snapshot."""
    targets = parse_csv_targets(csv_path)
    return CourseTargets(
        catalog_edition=catalog_edition,
        catalog_url_template=CATALOG_URL_TEMPLATE,
        targets=targets,
    )


def render_toml(config: CourseTargets) -> str:
    """Serialize CourseTargets to the [[targets]] array-of-tables shape load_targets consumes."""
    lines = [
        f'catalog_edition = "{config.catalog_edition}"',
        f'catalog_url_template = "{config.catalog_url_template}"',
        "",
    ]
    for target in config.targets:
        lines.append("[[targets]]")
        lines.append(f'subject = "{target.subject}"')
        lines.append(f'number = "{target.number}"')
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reproducibly generate config/course_targets.toml from courses.csv."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Source CSV path.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output TOML path.")
    parser.add_argument(
        "--catalog-edition",
        default=DEFAULT_CATALOG_EDITION,
        help="Catalog edition, e.g. 2026-2027.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = build_targets(args.csv, catalog_edition=args.catalog_edition)
    args.out.write_text(render_toml(config), encoding="utf-8")
    print(f"Generated {len(config.targets)} targets -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
