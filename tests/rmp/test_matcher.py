from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from easy_a.rmp.client import RmpSearchClient, parse_teachers
from easy_a.rmp.matcher import (
    Match,
    MatchMethod,
    RmpTeacher,
    apply_overrides,
    fold,
    link_key,
    match_teacher,
    parse_name,
)


def teacher(legacy_id: int, first: str, last: str, *codes: str, ratings: int = 5) -> RmpTeacher:
    return RmpTeacher(legacy_id, first, last, "Dept", tuple(codes), ratings)


@pytest.mark.parametrize(
    ("name", "initial", "last"),
    [
        ("N. Volz", "n", "Volz"),
        ("J. A. Smith", "j", "Smith"),
        ("M  Garcia-Lopez", "m", "Garcia-Lopez"),
        ("A. Van Der Berg", "a", "Van Der Berg"),
        ("Volz", None, "Volz"),
    ],
)
def test_parse_name(name: str, initial: str | None, last: str) -> None:
    parsed = parse_name(name)
    assert parsed is not None
    assert (parsed.initial, parsed.last_name) == (initial, last)


def test_fold_and_key_ignore_accents_case_punctuation_and_spacing() -> None:
    assert fold("D’Ávila-Ruiz") == fold("davila ruiz") == "davilaruiz"
    assert link_key(" enc ", "N.  Volz") == "ENC|n. volz"


def test_unique_course_code_match_with_noisy_codes() -> None:
    volz = teacher(3028196, "Noah", "Volz", "1101", "ENC1101")
    assert match_teacher("N. Volz", "ENC", [volz]) == Match(3028196, MatchMethod.course_code)


def test_course_code_breaks_a_tie_between_same_initial_profiles() -> None:
    teachers = [
        teacher(1, "Steven", "Miller", "MAN3025"),
        teacher(2, "Scott", "Miller", "AMH 2020"),
        teacher(3, "Elizabeth", "Miller", "ANT2000"),
    ]
    assert match_teacher("S. Miller", "AMH", teachers) == Match(2, MatchMethod.course_code)


def test_ambiguous_same_initial_without_evidence_is_no_match() -> None:
    teachers = [teacher(1, "Steven", "Miller", "MAN3025"), teacher(2, "Scott", "Miller")]
    assert match_teacher("S. Miller", "ENC", teachers) is None


def test_two_profiles_both_evidenced_is_no_match() -> None:
    teachers = [teacher(1, "Sam", "Lee", "ENC1101"), teacher(2, "Sara", "Lee", "ENC1102")]
    assert match_teacher("S. Lee", "ENC", teachers) is None


def test_other_usf_subjects_count_as_evidence() -> None:
    teachers = [teacher(1, "Ann", "Bell", "AML2010"), teacher(2, "Amy", "Bell", "CHM2045")]
    match = match_teacher("A. Bell", "ENC", teachers, name_subjects={"ENC", "AML"})
    assert match == Match(1, MatchMethod.course_code)


def test_single_candidate_without_course_codes_is_accepted() -> None:
    assert match_teacher("J. Moy", "MAC", [teacher(7, "Jo", "Moy")]) == Match(7, MatchMethod.unique)


def test_single_candidate_teaching_something_else_is_rejected() -> None:
    # The only S. Miller on RMP teaches business; an English S. Miller is probably someone else.
    assert match_teacher("S. Miller", "ENC", [teacher(1, "Steven", "Miller", "MAN3025")]) is None


def test_initial_and_exact_last_name_are_required() -> None:
    teachers = [teacher(1, "Noah", "Volzer"), teacher(2, "Kim", "Volz")]
    assert match_teacher("N. Volz", "ENC", teachers) is None


def test_accented_and_hyphenated_last_names_match() -> None:
    teachers = [teacher(4, "José", "D'Ávila Ruiz", "SPN1120")]
    assert match_teacher("J. D’avila-Ruiz", "SPN", teachers) == Match(4, MatchMethod.course_code)


def test_duplicate_profiles_of_one_person_keep_the_most_rated() -> None:
    teachers = [
        teacher(10, "Austin", "Smith ", "PHY2048", ratings=2),
        teacher(11, "Austin", "Smith", "PHY2048", ratings=40),
    ]
    assert match_teacher("A. Smith", "PHY", teachers) == Match(11, MatchMethod.course_code)


def test_overrides_force_and_block() -> None:
    matches = {
        "ENC|n. volz": Match(1, MatchMethod.unique),
        "MAC|j. moy": Match(7, MatchMethod.unique),
    }
    merged = apply_overrides(matches, {"ENC|n. volz": 3028196, "MAC|j. moy": None})
    assert merged == {"ENC|n. volz": Match(3028196, MatchMethod.override), "MAC|j. moy": None}


def _graphql_page(nodes: list[dict[str, object]], *, next_cursor: str | None) -> dict[str, object]:
    return {
        "data": {
            "newSearch": {
                "teachers": {
                    "pageInfo": {"hasNextPage": next_cursor is not None, "endCursor": next_cursor},
                    "edges": [{"node": node} for node in nodes],
                }
            }
        }
    }


def test_client_paginates_caches_and_goes_offline(tmp_path: Path) -> None:
    node = {
        "legacyId": 3028196,
        "firstName": "Noah",
        "lastName": "Volz",
        "department": "English",
        "numRatings": 13,
        "courseCodes": [{"courseName": "ENC1101"}],
    }
    pages = [_graphql_page([node], next_cursor="c1"), _graphql_page([node], next_cursor=None)]
    seen: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content)["variables"]["after"])
        return httpx.Response(200, json=pages[len(seen) - 1])

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = RmpSearchClient(tmp_path, delay_seconds=0, http=http)
    assert [t.legacy_id for t in client.search("Volz") or []] == [3028196, 3028196]
    assert seen == [None, "c1"]

    offline = RmpSearchClient(tmp_path, offline=True)
    assert offline.search("Volz") == parse_teachers([node, node])
    assert offline.search("Nobody") is None
    assert offline.requests_made == 0


def test_truncated_schedule_names_match_the_full_surname_by_prefix() -> None:
    parsed = parse_name("K. Mavridou-Hernan")
    assert parsed is not None and parsed.truncated
    assert parsed.search_text == "Mavridou"
    teachers = [
        teacher(5, "Konstantina", "Mavridou-Hernandez", "ENC1101"),
        teacher(6, "Kim", "Mavridou", "ENC1101"),
    ]
    assert match_teacher("K. Mavridou-Hernan", "ENC", teachers) == Match(5, MatchMethod.course_code)


def test_short_names_still_need_an_exact_surname() -> None:
    parsed = parse_name("N. Volz")
    assert parsed is not None and not parsed.truncated
    assert parsed.search_text == "Volz"
    assert match_teacher("N. Volz", "ENC", [teacher(1, "Noah", "Volzer", "ENC1101")]) is None
