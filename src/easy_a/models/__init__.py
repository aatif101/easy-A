"""SQLAlchemy models for Easy-A."""

from easy_a.models.core import Course, CourseAttribute, GradeDistribution, IngestRun, Term

__all__ = [
    "Course",
    "CourseAttribute",
    "GradeDistribution",
    "IngestRun",
    "Term",
]
