from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Select, and_, exists, false, func, select
from sqlalchemy.sql.selectable import Subquery

from easy_a.analytics.confidence import LOW_CONFIDENCE_MAX_EFFECTIVE_N
from easy_a.analytics.scoring import ScoreConfig
from easy_a.api.dependencies import BannerTerm, DbSession
from easy_a.common.section_types import LABORATORY_SECTION_TYPES
from easy_a.models import Course, GradeDistribution, Section, SectionInstructor, Term
from easy_a.search import parse_query, text_match

router = APIRouter(prefix="/api/v1/search", tags=["search"])
IDENTITY_NOTE = (
    "College identity is unavailable in stored records. Each listed name is kept within one "
    "course; matching names across courses are not proof of the same person. Initials are not "
    "expanded. Ambiguous assignments are excluded."
)
UNAVAILABLE_NAMES = ("", "staff", "tba", "tbd", "arr", "unknown", "unavailable", "n/a", "none")


class CourseMatch(BaseModel):
    course_id: int
    subject: str
    course_number: str
    title: str
    catalog_edition: str
    current_sections: int


class InstructorMatch(CourseMatch):
    name: str
    historical_sections: int
    observed_at: datetime


class SearchResponse(BaseModel):
    as_of: datetime
    kind: str
    subject: str
    course_number: str
    crn: str | None
    courses: list[CourseMatch]
    instructors: list[InstructorMatch]
    course_total: int
    instructor_total: int
    limit: int
    offset: int
    identity_note: str = IDENTITY_NOTE


class GradeRecord(BaseModel):
    term: str
    crn: str
    counts: dict[str, int]
    source: str
    source_hash: str
    ingested_at: datetime


class HistoryResponse(BaseModel):
    course: CourseMatch
    name: str | None
    status: str
    a_share: float | None
    observed_grade_count: int
    counts: dict[str, int]
    terms: list[str]
    items: list[GradeRecord]
    total: int
    limit: int
    offset: int
    identity_note: str = IDENTITY_NOTE


def assignments() -> Subquery:
    """Only one usable name at the latest observation per section; stale names cannot match."""
    latest = (
        select(
            SectionInstructor.section_id,
            func.max(SectionInstructor.observed_at).label("observed_at"),
        )
        .group_by(SectionInstructor.section_id)
        .subquery()
    )
    return (
        select(
            SectionInstructor.section_id,
            func.trim(func.min(SectionInstructor.name_raw)).label("name"),
            latest.c.observed_at,
        )
        .join(
            latest,
            and_(
                latest.c.section_id == SectionInstructor.section_id,
                latest.c.observed_at == SectionInstructor.observed_at,
            ),
        )
        .group_by(SectionInstructor.section_id, latest.c.observed_at)
        .having(func.count(func.distinct(func.lower(func.trim(SectionInstructor.name_raw)))) == 1)
        .having(
            func.lower(func.trim(func.min(SectionInstructor.name_raw))).not_in(UNAVAILABLE_NAMES)
        )
        .subquery()
    )


def safe_historical_assignments() -> Select[Any]:
    return (
        select(SectionInstructor.section_id)
        .group_by(SectionInstructor.section_id)
        .having(func.count(func.distinct(func.lower(func.trim(SectionInstructor.name_raw)))) == 1)
    )


def current_count(term: str) -> Any:
    return (
        select(func.count(Section.id))
        .join(Term)
        .where(
            Section.course_id == Course.id,
            Term.banner_code == term,
            Section.removed_at.is_(None),
        )
        .correlate(Course)
        .scalar_subquery()
    )


def course_model(course: Course, count: int) -> CourseMatch:
    return CourseMatch(
        course_id=course.id,
        subject=course.subject,
        course_number=course.number,
        title=course.title,
        catalog_edition=course.catalog_edition,
        current_sections=count,
    )


@router.get("", response_model=SearchResponse)
def discover(
    term: BannerTerm,
    session: DbSession,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> SearchResponse:
    query = parse_query(q)
    courses = select(Course, current_count(term).label("current_sections"))
    if query.kind == "crn":
        courses = courses.where(
            exists(
                select(1)
                .select_from(Section)
                .join(Term)
                .where(
                    Section.course_id == Course.id,
                    Section.crn == query.text,
                    Term.banner_code == term,
                    Section.removed_at.is_(None),
                )
            )
        )
    elif query.kind == "course":
        courses = courses.where(Course.subject == query.subject, Course.number == query.number)
    elif query.kind == "number":
        courses = courses.where(Course.number == query.number)
    elif query.kind == "subject":
        courses = courses.where(Course.subject == query.subject)
    elif query.kind == "text":
        courses = courses.where(text_match(Course.title, query.text, title=True))
    else:
        courses = courses.where(false())
    course_total = session.scalar(select(func.count()).select_from(courses.subquery())) or 0
    course_rows = session.execute(
        courses.order_by(Course.subject, Course.number, Course.id).limit(limit).offset(offset)
    ).all()

    assigned = assignments()
    instructors = (
        select(
            Course,
            assigned.c.name,
            func.max(assigned.c.observed_at).label("observed_at"),
            func.sum(
                func.cast(
                    and_(Term.banner_code == term, Section.removed_at.is_(None)),
                    type_=Section.id.type,
                )
            ).label("current_sections"),
            func.sum(func.cast(Term.banner_code < term, type_=Section.id.type)).label(
                "historical_sections"
            ),
        )
        .join(Section, Section.course_id == Course.id)
        .join(Term, Term.id == Section.term_id)
        .join(assigned, assigned.c.section_id == Section.id)
        .where(Term.banner_code <= term, (Term.banner_code < term) | Section.removed_at.is_(None))
        .where((Term.banner_code == term) | Section.id.in_(safe_historical_assignments()))
        .where(text_match(assigned.c.name, query.text) if query.text else false())
        .group_by(Course.id, assigned.c.name)
    )
    instructor_total = session.scalar(select(func.count()).select_from(instructors.subquery())) or 0
    instructor_rows = session.execute(
        instructors.order_by(Course.subject, Course.number, Course.id, assigned.c.name)
        .limit(limit)
        .offset(offset)
    ).all()
    return SearchResponse(
        as_of=datetime.now(UTC),
        kind=query.kind,
        subject=query.subject,
        course_number=query.number,
        crn=query.text if query.kind == "crn" else None,
        courses=[course_model(c, n) for c, n in course_rows],
        instructors=[
            InstructorMatch(
                **course_model(row[0], row.current_sections).model_dump(),
                name=row.name,
                historical_sections=row.historical_sections,
                observed_at=row.observed_at,
            )
            for row in instructor_rows
        ],
        course_total=course_total,
        instructor_total=instructor_total,
        limit=limit,
        offset=offset,
    )


BUCKETS = ("a", "b", "c", "d", "f", "i", "s", "u", "w", "other")


def history_query(course_id: int, term: str, name: str | None) -> Select[Any]:
    stmt = select(GradeDistribution, Term.banner_code).join(Term).where(Term.banner_code < term)
    if name is None:
        # Same course attribution / term+CRN backstop as the existing analytics.
        stmt = stmt.outerjoin(
            Section,
            and_(
                Section.term_id == GradeDistribution.term_id, Section.crn == GradeDistribution.crn
            ),
        ).where((GradeDistribution.course_id == course_id) | (Section.course_id == course_id))
    else:
        assigned = assignments()
        # Existing analytics uses any historical assignment. Where assignments changed or
        # conflict, discovery declines attribution rather than turning names into identity.
        safe = safe_historical_assignments()
        stmt = (
            stmt.join(
                Section,
                and_(
                    Section.term_id == GradeDistribution.term_id,
                    Section.crn == GradeDistribution.crn,
                ),
            )
            .join(assigned, assigned.c.section_id == Section.id)
            .where(
                Section.course_id == course_id,
                assigned.c.name == name,
                Section.id.in_(safe),
                func.lower(func.trim(Section.section_type)).not_in(LABORATORY_SECTION_TYPES),
            )
        )
    return stmt


@router.get("/history", response_model=HistoryResponse)
def history(
    term: BannerTerm,
    session: DbSession,
    course_id: Annotated[int, Query(ge=1)],
    name: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> HistoryResponse:
    row = session.execute(select(Course, current_count(term)).where(Course.id == course_id)).first()
    if row is None:
        raise HTTPException(404, "Course not found.")
    stmt = history_query(course_id, term, name)
    evidence = stmt.subquery()
    totals = session.execute(
        select(
            func.count(),
            *[func.coalesce(func.sum(evidence.c[f"{bucket}_count"]), 0) for bucket in BUCKETS],
        ).select_from(evidence)
    ).one()
    total = int(totals[0])
    counts = {bucket: int(totals[index + 1]) for index, bucket in enumerate(BUCKETS)}
    observed = sum(counts[bucket] for bucket in ("a", "b", "c", "d", "f"))
    terms = list(
        session.scalars(select(evidence.c.banner_code).distinct().order_by(evidence.c.banner_code))
    )
    rows = session.execute(
        stmt.order_by(Term.banner_code.desc(), GradeDistribution.crn, GradeDistribution.source)
        .limit(limit)
        .offset(offset)
    ).all()
    status = (
        "unavailable"
        if not total
        else "no_letter_grades"
        if not observed
        else "insufficient"
        if observed
        < (
            ScoreConfig().instructor_course_min_effective_n
            if name is not None
            else LOW_CONFIDENCE_MAX_EFFECTIVE_N
        )
        else "available"
    )
    return HistoryResponse(
        course=course_model(row[0], row[1]),
        name=name,
        status=status,
        a_share=counts["a"] / observed if observed else None,
        observed_grade_count=observed,
        counts=counts,
        terms=terms,
        items=[
            GradeRecord(
                term=code,
                crn=grade.crn,
                counts={bucket: getattr(grade, f"{bucket}_count") for bucket in BUCKETS},
                source=grade.source,
                source_hash=grade.source_hash,
                ingested_at=grade.ingested_at,
            )
            for grade, code in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
