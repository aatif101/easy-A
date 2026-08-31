from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from easy_a.catalog.parser import CatalogCourse, CatalogParseError, parse_catalog_html
from easy_a.models import Course, CourseAttribute, IngestRun

CATALOG_SOURCE = "usf_catalog"


@dataclass(frozen=True)
class CatalogIngestResult:
    records_seen: int
    records_inserted: int
    records_updated: int
    ingest_run_id: int


def ingest_catalog_html(
    session: Session,
    html: str,
    catalog_edition: str,
    source: str = CATALOG_SOURCE,
) -> CatalogIngestResult:
    run = IngestRun(
        source=source,
        status="running",
        records_seen=0,
        records_inserted=0,
        records_updated=0,
        records_failed=0,
    )
    session.add(run)
    session.flush()

    try:
        courses = parse_catalog_html(html, catalog_edition)
        inserted, updated = upsert_catalog_courses(session, courses)
    except CatalogParseError as exc:
        run.status = "failed"
        run.finished_at = datetime.now(UTC)
        run.error_message = str(exc)
        run.records_failed = 1
        session.flush()
        raise

    run.status = "succeeded"
    run.finished_at = datetime.now(UTC)
    run.records_seen = len(courses)
    run.records_inserted = inserted
    run.records_updated = updated
    session.flush()

    return CatalogIngestResult(
        records_seen=len(courses),
        records_inserted=inserted,
        records_updated=updated,
        ingest_run_id=run.id,
    )


def upsert_catalog_courses(session: Session, courses: list[CatalogCourse]) -> tuple[int, int]:
    inserted = 0
    updated = 0

    for parsed_course in courses:
        course = session.execute(
            select(Course).where(
                Course.subject == parsed_course.subject,
                Course.number == parsed_course.number,
                Course.catalog_edition == parsed_course.catalog_edition,
            )
        ).scalar_one_or_none()

        if course is None:
            session.add(_new_course(parsed_course))
            inserted += 1
            continue

        if _course_differs(course, parsed_course):
            course.title = parsed_course.title
            course.credits = parsed_course.credits
            course.description = parsed_course.description
            course.prerequisites = parsed_course.prerequisites
            course.other_information = parsed_course.other_information
            session.execute(delete(CourseAttribute).where(CourseAttribute.course_id == course.id))
            course.attributes = [
                CourseAttribute(
                    attribute_code=attribute.attribute_code,
                    attribute_label=attribute.attribute_label,
                )
                for attribute in parsed_course.attributes
            ]
            updated += 1

    session.flush()
    return inserted, updated


def _new_course(parsed_course: CatalogCourse) -> Course:
    return Course(
        subject=parsed_course.subject,
        number=parsed_course.number,
        title=parsed_course.title,
        credits=parsed_course.credits,
        description=parsed_course.description,
        prerequisites=parsed_course.prerequisites,
        other_information=parsed_course.other_information,
        catalog_edition=parsed_course.catalog_edition,
        attributes=[
            CourseAttribute(
                attribute_code=attribute.attribute_code,
                attribute_label=attribute.attribute_label,
            )
            for attribute in parsed_course.attributes
        ],
    )


def _course_differs(course: Course, parsed_course: CatalogCourse) -> bool:
    existing_attributes = [
        (attribute.attribute_code, attribute.attribute_label) for attribute in course.attributes
    ]
    incoming_attributes = [
        (attribute.attribute_code, attribute.attribute_label)
        for attribute in parsed_course.attributes
    ]
    return (
        course.title != parsed_course.title
        or course.credits != parsed_course.credits
        or course.description != parsed_course.description
        or course.prerequisites != parsed_course.prerequisites
        or course.other_information != parsed_course.other_information
        or existing_attributes != incoming_attributes
    )
