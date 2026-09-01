from __future__ import annotations

from easy_a.catalog.parser import parse_catalog_html

COURSE_INVENTORY_HTML = """
<html>
  <body>
    <h1>ENC 1101: Composition I</h1>
    <table>
      <tr><th>Description:</th><td>This course introduces rhetorical concepts.</td></tr>
      <tr><th>Credit Hours:</th><td>3</td></tr>
      <tr><th>Prerequisites:</th><td></td></tr>
      <tr><th>Other Information:</th><td>Scores of: STI1 of 440.</td></tr>
    </table>
    <h2>Course Attributes(s)</h2>
    <table>
      <tr>
        <th>One USF</th>
        <td>
          General Education Core Communication (SGEC),
          State Communication Requirement (6AC),
          USFSM State Comm Req. (6ACM)
        </td>
      </tr>
    </table>
  </body>
</html>
"""


COURSEBLOCK_HTML = """
<html>
  <body>
    <div class="courseblock">
      <p class="courseblocktitle"><strong>MAC 1105 College Algebra Credit Hours: 3</strong></p>
      <p class="courseblockdesc">Linear equations, functions, and graphing.</p>
      <p><strong>Prerequisite(s):</strong> C or better in MAT 1033.</p>
      <p>
        <strong>Other Information:</strong>
        May not receive credit for both MAC 1105 and MAC 1147.
      </p>
      <p>
        <strong>Attribute(s):</strong>
        6AM - State Mathematics Requirement;
        SGEM - General Education Core Mathematics;
        SGEM - State GE Core Math
      </p>
    </div>
  </body>
</html>
"""


def test_parse_course_inventory_fixture() -> None:
    courses = parse_catalog_html(COURSE_INVENTORY_HTML, catalog_edition="2026-2027")

    assert len(courses) == 1
    course = courses[0]
    assert course.subject == "ENC"
    assert course.number == "1101"
    assert course.title == "Composition I"
    assert course.credits == "3"
    assert course.description == "This course introduces rhetorical concepts."
    assert course.other_information == "Scores of: STI1 of 440."
    assert [
        (attribute.attribute_code, attribute.attribute_label) for attribute in course.attributes
    ] == [
        ("SGEC", "General Education Core Communication"),
        ("6AC", "State Communication Requirement"),
        ("6ACM", "USFSM State Comm Req."),
    ]


def test_parse_courseblock_fixture_preserves_repeated_attribute_codes() -> None:
    courses = parse_catalog_html(COURSEBLOCK_HTML, catalog_edition="2026-2027")

    assert len(courses) == 1
    course = courses[0]
    assert course.subject == "MAC"
    assert course.number == "1105"
    assert course.title == "College Algebra"
    assert course.credits == "3"
    assert course.prerequisites == "C or better in MAT 1033."
    assert [
        (attribute.attribute_code, attribute.attribute_label) for attribute in course.attributes
    ] == [
        ("6AM", "State Mathematics Requirement"),
        ("SGEM", "General Education Core Mathematics"),
        ("SGEM", "State GE Core Math"),
    ]
