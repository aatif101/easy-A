from __future__ import annotations

from urllib.parse import parse_qs

import httpx
import pytest

from easy_a.schedule.client import (
    RESULTS_PATH,
    ScheduleSearchQuery,
    StaffScheduleClient,
    build_form_data,
)


def test_spring_2027_query_builds_validated_form_fields() -> None:
    data = build_form_data(
        ScheduleSearchQuery(term="202701", campus="t", subject="mac", course="1105")
    )

    assert data["P_SEMESTER"] == "202701"
    assert data["P_CAMPUS"] == "T"
    assert data["P_SUBJ"] == "MAC"
    assert data["P_NUM"] == "1105"
    assert data["p_insm_x_incl"] == "YCL"


def test_search_uses_post_results_endpoint() -> None:
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["method"] = request.method
        observed["path"] = request.url.path
        observed["form"] = parse_qs(request.content.decode())
        return httpx.Response(200, text="<html>results</html>")

    transport = httpx.MockTransport(handler)
    with httpx.Client(base_url="https://usfweb.usf.edu", transport=transport) as http_client:
        client = StaffScheduleClient(http_client)
        html = client.search(ScheduleSearchQuery(term="202408", crn="89033"))

    assert html == "<html>results</html>"
    assert observed["method"] == "POST"
    assert observed["path"] == RESULTS_PATH
    assert observed["form"] == {
        "P_SEMESTER": ["202408"],
        "P_REF": ["89033"],
        **{
            key: [value]
            for key, value in build_form_data(
                ScheduleSearchQuery(term="202408", crn="89033")
            ).items()
            if value and key not in {"P_SEMESTER", "P_REF"}
        },
    }


def test_query_must_be_narrow_and_term_must_be_six_digits() -> None:
    with pytest.raises(ValueError, match="narrow"):
        ScheduleSearchQuery(term="202701")
    with pytest.raises(ValueError, match="six digits"):
        ScheduleSearchQuery(term="Spring 2027", subject="MAC")


def test_query_rejects_empty_crn() -> None:
    with pytest.raises(ValueError, match="CRN"):
        ScheduleSearchQuery(term="202408", crn=" ")
