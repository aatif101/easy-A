from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

BASE_URL = "https://usf.simplesyllabus.com"
DEFAULT_USER_AGENT = "Easy-A data pipeline (https://github.com/aatif101/easy-A)"
_DOCUMENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class SimpleSyllabusClient:
    def __init__(
        self,
        http_client: httpx.Client | None = None,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            base_url=BASE_URL,
            follow_redirects=True,
            timeout=timeout_seconds,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )

    def fetch_document_html(self, document_id_or_url: str) -> tuple[str, str]:
        document_id = extract_document_id(document_id_or_url)
        response = self._client.get(f"/api2/doc-html/{document_id}")
        response.raise_for_status()
        return document_id, response.text

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> SimpleSyllabusClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def extract_document_id(document_id_or_url: str) -> str:
    value = document_id_or_url.strip()
    if not value:
        raise ValueError("Simple Syllabus document ID cannot be empty.")
    if "://" in value:
        parsed = urlparse(value)
        if parsed.hostname != "usf.simplesyllabus.com":
            raise ValueError("Only public usf.simplesyllabus.com document URLs are supported.")
        value = parsed.path.rstrip("/").split("/")[-1]
    if not _DOCUMENT_ID_RE.fullmatch(value):
        raise ValueError(f"Invalid Simple Syllabus document ID {value!r}.")
    return value


def build_view_url(document_id: str) -> str:
    return f"{BASE_URL}/en-US/doc/{extract_document_id(document_id)}?mode=view"
