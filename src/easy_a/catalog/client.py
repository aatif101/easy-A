from __future__ import annotations

import httpx

DEFAULT_USER_AGENT = "Easy-A data pipeline (https://github.com/aatif101/easy-A)"


def fetch_catalog_html(url: str, timeout_seconds: float = 30.0) -> str:
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    with httpx.Client(follow_redirects=True, timeout=timeout_seconds, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text
