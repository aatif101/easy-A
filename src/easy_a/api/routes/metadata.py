from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from easy_a.api.dependencies import DbSession
from easy_a.api.schemas import (
    DeliveryMethodMetadata,
    GenEdAttributeMetadata,
    SubjectMetadata,
    TermMetadata,
)
from easy_a.models import Course, CourseAttribute, Section, Term
from easy_a.schedule.normalize import DELIVERY_METHOD_LABELS

router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])


@router.get("/terms", response_model=list[TermMetadata])
def list_terms(session: DbSession) -> list[TermMetadata]:
    terms = session.execute(select(Term).order_by(Term.banner_code.desc())).scalars().all()
    return [
        TermMetadata(
            term=term.banner_code,
            term_name=term.name,
            year=term.year,
            season=term.season,
        )
        for term in terms
    ]


@router.get("/subjects", response_model=list[SubjectMetadata])
def list_subjects(session: DbSession) -> list[SubjectMetadata]:
    subjects = session.execute(
        select(Course.subject).distinct().order_by(Course.subject)
    ).scalars()
    return [SubjectMetadata(subject=subject) for subject in subjects]


@router.get("/gened-attributes", response_model=list[GenEdAttributeMetadata])
def list_gened_attributes(session: DbSession) -> list[GenEdAttributeMetadata]:
    rows = session.execute(
        select(CourseAttribute.attribute_code, CourseAttribute.attribute_label)
        .distinct()
        .order_by(CourseAttribute.attribute_code, CourseAttribute.attribute_label)
    )
    return [
        GenEdAttributeMetadata(code=code, label=label)
        for code, label in rows
    ]


@router.get("/delivery-methods", response_model=list[DeliveryMethodMetadata])
def list_delivery_methods(session: DbSession) -> list[DeliveryMethodMetadata]:
    codes = session.execute(
        select(Section.delivery_method)
        .where(Section.delivery_method.is_not(None))
        .distinct()
        .order_by(Section.delivery_method)
    ).scalars()
    return [
        DeliveryMethodMetadata(code=code, label=DELIVERY_METHOD_LABELS.get(code))
        for code in codes
        if code is not None
    ]
