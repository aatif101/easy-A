"""One-time, rate-limited lookup of USF profiles on Rate My Professors (PROJECT.md D-08 amendment).

Uses the same public GraphQL search the RMP website calls, one request per distinct last name,
sequentially, with responses cached on disk so a rerun or resume never asks twice. Only the
fields needed to pick a profile are requested; nothing here is stored except by the caller,
which keeps the ``legacyId`` alone.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from easy_a.rmp.matcher import RmpTeacher, fold

GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
USF_SCHOOL_ID = "U2Nob29sLTEyNjI="  # base64("School-1262"), University of South Florida
USER_AGENT = "easy-A RMP link matcher (one-time lookup; stores profile ids only)"
# The credential the RMP website itself sends; it is public and not an account.
_AUTHORIZATION = "Basic dGVzdDp0ZXN0"

_QUERY = """
query Search($text: String!, $schoolID: ID!, $after: String) {
  newSearch {
    teachers(query: {text: $text, schoolID: $schoolID}, first: 50, after: $after) {
      pageInfo { hasNextPage endCursor }
      edges { node { legacyId firstName lastName department numRatings
                     courseCodes { courseName } } }
    }
  }
}
"""


def parse_teachers(nodes: list[dict[str, Any]]) -> list[RmpTeacher]:
    return [
        RmpTeacher(
            legacy_id=int(node["legacyId"]),
            first_name=(node.get("firstName") or "").strip(),
            last_name=(node.get("lastName") or "").strip(),
            department=(node.get("department") or "").strip(),
            course_codes=tuple(
                code["courseName"]
                for code in node.get("courseCodes") or ()
                if code.get("courseName")
            ),
            num_ratings=int(node.get("numRatings") or 0),
        )
        for node in nodes
    ]


class RmpSearchClient:
    def __init__(
        self,
        cache_dir: Path,
        *,
        delay_seconds: float = 1.0,
        offline: bool = False,
        http: httpx.Client | None = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.delay_seconds = delay_seconds
        self.offline = offline
        self.requests_made = 0
        self._http = http
        self._last_request = 0.0

    def search(self, last_name: str) -> list[RmpTeacher] | None:
        """USF profiles for this last name; None when offline and not cached."""
        cache_file = self.cache_dir / f"{fold(last_name)}.json"
        if cache_file.exists():
            return parse_teachers(json.loads(cache_file.read_text(encoding="utf-8")))
        if self.offline:
            return None
        nodes = self._fetch_all(last_name)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(nodes, ensure_ascii=False), encoding="utf-8")
        return parse_teachers(nodes)

    def _fetch_all(self, last_name: str) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        after: str | None = None
        while True:
            page = self._post({"text": last_name, "schoolID": USF_SCHOOL_ID, "after": after})
            teachers = page["data"]["newSearch"]["teachers"]
            nodes.extend(edge["node"] for edge in teachers["edges"])
            if not teachers["pageInfo"]["hasNextPage"]:
                return nodes
            after = teachers["pageInfo"]["endCursor"]

    def _post(self, variables: dict[str, Any]) -> dict[str, Any]:
        wait = self._last_request + self.delay_seconds - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        http = self._http or httpx.Client(timeout=20.0)
        try:
            response = http.post(
                GRAPHQL_URL,
                json={"query": _QUERY, "variables": variables},
                headers={"Authorization": _AUTHORIZATION, "User-Agent": USER_AGENT},
            )
        finally:
            self._last_request = time.monotonic()
            self.requests_made += 1
            if self._http is None:
                http.close()
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        if payload.get("errors"):
            raise RuntimeError(f"RMP search error: {payload['errors']}")
        return payload
