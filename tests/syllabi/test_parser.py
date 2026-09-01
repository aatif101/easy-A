from __future__ import annotations

from pathlib import Path

from easy_a.syllabi.parser import hash_content_text, normalize_content_text, parse_syllabus_html

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_syllabus_metadata_crn_and_complete_content_are_parsed() -> None:
    html = (FIXTURES / "syllabus_enc_1101.html").read_text(encoding="utf-8")
    syllabus = parse_syllabus_html(
        html,
        document_id="bpvdotxa9",
        organization="University of South Florida",
    )

    assert syllabus.document_id == "bpvdotxa9"
    assert syllabus.term_code == "202605"
    assert syllabus.subject == "ENC"
    assert syllabus.course_number == "1101"
    assert syllabus.section_number == "521"
    assert syllabus.crn == "50750"
    assert syllabus.instructor_raw == "Dr. Kara Taczak"
    assert syllabus.organization == "University of South Florida"
    assert syllabus.title == "Composition I"
    assert "Course Description Writing as a process" in syllabus.content_text
    assert "Student Learning Outcomes Compose clear academic arguments." in syllabus.content_text
    assert syllabus.content_html == html


def test_content_normalization_and_hashing_are_stable() -> None:
    first = normalize_content_text("Course\u00a0Description\n\n  Text")
    second = normalize_content_text("Course Description Text")

    assert first == second
    assert hash_content_text(first) == hash_content_text(second)
