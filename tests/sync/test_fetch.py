from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import parse_qs

import httpx
import pytest

from easy_a.schedule.client import (
    DEFAULT_USER_AGENT,
    RESULTS_PATH,
    ScheduleSearchQuery,
    StaffScheduleClient,
    WholeTermResponseError,
    build_form_data,
)
from easy_a.schedule.normalize import normalize_schedule_row
from easy_a.schedule.parser import ScheduleParseError, parse_schedule_html
from easy_a.sync.fetch import fetch_whole_term, parse_whole_term
from easy_a.sync.scope import (
    SweepScopeError,
    apply_scope,
    is_undergraduate_number,
)
from tests.sync.wholeterm_html import RowSpec, build_whole_term_html, sequential_rows

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def _client(handler: httpx.MockTransport) -> tuple[httpx.Client, StaffScheduleClient]:
    http = httpx.Client(
        base_url="https://usfweb.usf.edu",
        transport=handler,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    return http, StaffScheduleClient(http)


def test_search_term_posts_one_whole_term_request() -> None:
    seen: list[httpx.Request] = []
    html = build_whole_term_html(sequential_rows(3))

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text=html, headers={"content-type": "text/html; charset=utf-8"})

    http, client = _client(httpx.MockTransport(handler))
    with http:
        page = client.search_term("202701")

    assert len(seen) == 1
    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == RESULTS_PATH
    assert request.headers["user-agent"] == DEFAULT_USER_AGENT
    form = parse_qs(request.content.decode(), keep_blank_values=True)
    assert form["P_SEMESTER"] == ["202701"]
    assert form["P_CAMPUS"] == ["T"]
    assert form["P_SUBJ"] == [""]
    assert form["P_REF"] == [""]
    assert form["P_NUM"] == [""]
    assert page.html == html
    assert page.byte_count == len(html.encode())
    assert page.content_type.startswith("text/html")
    assert page.content_encoding is None
    assert page.elapsed_seconds >= 0


def test_whole_term_campus_defaults_to_tampa_and_is_passed_through_explicitly() -> None:
    """The live sync never names a campus, so it keeps campus=T; the backfill names its own."""
    seen: list[str] = []
    html = build_whole_term_html(sequential_rows(2))

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(parse_qs(request.content.decode(), keep_blank_values=True)["P_CAMPUS"][0])
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    http, client = _client(httpx.MockTransport(handler))
    with http:
        client.search_term("202701")
        fetch_whole_term(client, "202701", now_fn=lambda: NOW)
        fetch_whole_term(client, "202701", now_fn=lambda: NOW, campus="")

    assert seen == ["T", "T", ""]


def test_search_term_reports_content_encoding_and_uses_long_read_timeout() -> None:
    timeouts: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        timeouts.append(request.extensions["timeout"])
        return httpx.Response(200, text="<html></html>", headers={"content-type": "text/html"})

    http, client = _client(httpx.MockTransport(handler))
    with http:
        client.search_term("202701")

    assert timeouts == [{"connect": 15.0, "read": 120.0, "write": 120.0, "pool": 120.0}]


def test_search_term_rejects_non_html_content_type() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, content=b"{}", headers={"content-type": "application/json"}
        )
    )
    http, client = _client(transport)
    with http, pytest.raises(WholeTermResponseError, match="Content-Type"):
        client.search_term("202701")


def test_search_term_rejects_oversized_body() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, content=b"x" * 5000, headers={"content-type": "text/html"}
        )
    )
    http, client = _client(transport)
    with http, pytest.raises(WholeTermResponseError, match="exceeded"):
        client.search_term("202701", max_bytes=1000)


def test_search_term_does_not_loosen_narrow_query_validation() -> None:
    with pytest.raises(ValueError, match="narrow"):
        ScheduleSearchQuery(term="202701")
    # The narrow form builder is unchanged for a real narrow query.
    assert (
        build_form_data(ScheduleSearchQuery(term="202701", campus="t", subject="mac"))["P_SUBJ"]
        == "MAC"
    )


def test_chunked_parse_equals_single_full_parse() -> None:
    specs = sequential_rows(600)
    html = build_whole_term_html(specs, error_tail=False)

    chunked = parse_whole_term(html, chunk_rows=250)
    full = [normalize_schedule_row(row) for row in parse_schedule_html(html)]

    assert len(chunked.rows) == 600
    assert list(chunked.rows) == full
    assert chunked.data_row_count == 600
    assert chunked.tail_error is False


def test_error_tail_is_tolerated_and_recorded() -> None:
    html = build_whole_term_html(sequential_rows(10), error_tail=True)
    assert "</table>" not in html.lower()

    parsed = parse_whole_term(html)

    assert len(parsed.rows) == 10
    assert parsed.tail_error is True


def test_missing_header_fails_closed() -> None:
    html = build_whole_term_html(sequential_rows(5), include_header=False)
    with pytest.raises(ScheduleParseError, match="headers were not found"):
        parse_whole_term(html)


def test_short_row_fails_closed_with_both_counts() -> None:
    specs = sequential_rows(20)
    html = build_whole_term_html(specs, malformed_crns=[specs[7].crn])
    with pytest.raises(ScheduleParseError, match=r"Parsed 19 rows from 20 data rows"):
        parse_whole_term(html)


def test_fetch_whole_term_round_trip_keeps_metadata_not_html() -> None:
    html = build_whole_term_html(sequential_rows(4))
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=html, headers={"content-type": "text/html"})
    )
    http, client = _client(transport)
    with http:
        fetched = fetch_whole_term(client, "202701", now_fn=lambda: NOW)

    assert len(fetched.parse.rows) == 4
    assert fetched.byte_count == len(html.encode())
    assert fetched.fetched_at == NOW
    assert not hasattr(fetched, "html")


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        ("0001", True),
        ("1105", True),
        ("2045L", True),
        ("4999", True),
        ("5000", False),
        ("6320", False),
        ("ABCD", False),
        ("12", False),
        ("", False),
    ],
)
def test_is_undergraduate_number(number: str, expected: bool) -> None:
    assert is_undergraduate_number(number) is expected


def test_apply_scope_keeps_undergraduate_tampa_only() -> None:
    specs = [
        RowSpec(crn="1", number="0001"),
        RowSpec(crn="2", number="1105"),
        RowSpec(crn="3", subject="CHM", number="2045L"),
        RowSpec(crn="4", number="4999"),
        RowSpec(crn="5", number="5000"),
        RowSpec(crn="6", number="6320"),
        RowSpec(crn="7", subject="ENC", number="ABCD"),
        RowSpec(crn="8", number="1105", campus="Sarasota-Manatee"),
    ]
    rows = parse_whole_term(build_whole_term_html(specs)).rows

    in_scope, report = apply_scope(rows)

    assert [row.crn for row in in_scope] == ["1", "2", "3", "4"]
    assert report.total_rows == 8
    assert report.distinct_crns == 8
    assert report.non_tampa_rows == 1
    assert report.graduate_rows == 2
    assert report.unparseable_number_rows == 1
    assert report.in_scope_rows == 4


def test_apply_scope_rejects_duplicate_in_scope_crn() -> None:
    rows = parse_whole_term(
        build_whole_term_html([RowSpec(crn="9"), RowSpec(crn="9", section="002")])
    ).rows
    with pytest.raises(SweepScopeError, match="9"):
        apply_scope(rows)


def test_scope_report_counts_on_mixed_sample() -> None:
    specs: list[RowSpec] = []
    for i in range(30):  # in scope: 3 subjects, 10 courses, 3 sections each
        course = i // 3
        subject = ("MAC", "ENC", "CHM")[course % 3]
        specs.append(RowSpec(crn=str(100 + i), subject=subject, number=str(1000 + course)))
    for i in range(12):  # graduate
        specs.append(RowSpec(crn=str(200 + i), subject="EDF", number="6000"))
    for i in range(5):  # non-Tampa
        specs.append(RowSpec(crn=str(300 + i), campus="St. Petersburg"))
    for i in range(3):  # unparseable
        specs.append(RowSpec(crn=str(400 + i), subject="ART", number="XYZ1"))
    rows = parse_whole_term(build_whole_term_html(specs)).rows

    in_scope, report = apply_scope(rows)

    assert len(in_scope) == 30
    assert report.total_rows == 50
    assert report.distinct_crns == 50
    assert report.non_tampa_rows == 5
    assert report.graduate_rows == 12
    assert report.unparseable_number_rows == 3
    assert report.in_scope_rows == 30
    assert report.subjects == frozenset({"MAC", "ENC", "CHM"})
    assert len(report.course_keys) == 10
    assert report.as_dict()["in_scope_rows"] == 30
