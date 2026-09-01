from __future__ import annotations

import httpx
import pytest

from easy_a.syllabi.client import SimpleSyllabusClient, extract_document_id


def test_extract_document_id_accepts_id_and_public_usf_url() -> None:
    assert extract_document_id("bpvdotxa9") == "bpvdotxa9"
    assert (
        extract_document_id("https://usf.simplesyllabus.com/en-US/doc/bpvdotxa9?mode=view")
        == "bpvdotxa9"
    )


def test_fetch_document_uses_public_html_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api2/doc-html/bpvdotxa9"
        return httpx.Response(200, text="<div>published syllabus</div>")

    transport = httpx.MockTransport(handler)
    with httpx.Client(
        base_url="https://usf.simplesyllabus.com", transport=transport
    ) as http_client:
        client = SimpleSyllabusClient(http_client)
        document_id, html = client.fetch_document_html("bpvdotxa9")

    assert document_id == "bpvdotxa9"
    assert html == "<div>published syllabus</div>"


def test_document_url_rejects_other_hosts() -> None:
    with pytest.raises(ValueError, match="Only public"):
        extract_document_id("https://example.com/en-US/doc/bpvdotxa9")
