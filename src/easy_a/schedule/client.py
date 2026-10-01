from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from easy_a.common.terms import normalize_banner_term_code

BASE_URL = "https://usfweb.usf.edu"
RESULTS_PATH = "/DSS/StaffScheduleSearch/StaffSearch/Results"
DEFAULT_USER_AGENT = "Easy-A data pipeline (https://github.com/aatif101/easy-A)"
WHOLE_TERM_MAX_BYTES = 25_000_000
WHOLE_TERM_READ_TIMEOUT_SECONDS = 120.0
WHOLE_TERM_CONNECT_TIMEOUT_SECONDS = 15.0

LIVE_WHOLE_TERM_CAMPUS = "T"
"""P_CAMPUS of the live sync's whole-term request: Tampa only (PROJECT.md D-22(a))."""

ALL_CAMPUSES = ""
"""A blank P_CAMPUS asks USF for every campus; only the one-off backfill uses it (gap 05)."""


class WholeTermResponseError(ValueError):
    """Raised when a whole-term response is not HTML or is implausibly large."""


@dataclass(frozen=True)
class WholeTermPage:
    """A whole-term response body plus the transport facts worth logging."""

    html: str
    byte_count: int
    content_type: str
    content_encoding: str | None
    elapsed_seconds: float


@dataclass(frozen=True)
class ScheduleSearchQuery:
    term: str
    campus: str | None = None
    subject: str | None = None
    course: str | None = None
    crn: str | None = None

    def __post_init__(self) -> None:
        normalize_banner_term_code(self.term)
        has_crn = self.crn is not None and bool(self.crn.strip())
        has_subject = self.subject is not None and bool(self.subject.strip())
        if self.crn is not None and not has_crn:
            raise ValueError("CRN cannot be empty.")
        if self.subject is not None and not has_subject:
            raise ValueError("Subject cannot be empty.")
        if not has_crn and not has_subject:
            raise ValueError("A narrow schedule search requires --crn or --subject.")


class StaffScheduleClient:
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

    def search(self, query: ScheduleSearchQuery) -> str:
        response = self._client.post(RESULTS_PATH, data=build_form_data(query))
        response.raise_for_status()
        return response.text

    def search_term(
        self,
        term: str,
        campus: str = LIVE_WHOLE_TERM_CAMPUS,
        *,
        max_bytes: int = WHOLE_TERM_MAX_BYTES,
        read_timeout_seconds: float = WHOLE_TERM_READ_TIMEOUT_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> WholeTermPage:
        """One whole-term POST (empty subject, CRN and course) for the live sync worker.

        This is the only path that omits a subject or CRN. It is deliberately separate from
        ScheduleSearchQuery so the narrow-search validation stays strict (PROJECT.md D-22(a)).
        """
        started = clock()
        timeout = httpx.Timeout(read_timeout_seconds, connect=WHOLE_TERM_CONNECT_TIMEOUT_SECONDS)
        with self._client.stream(
            "POST",
            RESULTS_PATH,
            data=build_whole_term_form_data(term, campus),
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type.lower():
                raise WholeTermResponseError(
                    f"Whole-term response Content-Type {content_type!r} is not text/html."
                )
            chunks: list[bytes] = []
            received = 0
            for chunk in response.iter_bytes():
                received += len(chunk)
                if received > max_bytes:
                    raise WholeTermResponseError(f"Whole-term response exceeded {max_bytes} bytes.")
                chunks.append(chunk)
            encoding = response.encoding or "utf-8"
            content_encoding = response.headers.get("content-encoding")
        body = b"".join(chunks)
        chunks.clear()
        return WholeTermPage(
            html=body.decode(encoding, errors="replace"),
            byte_count=received,
            content_type=content_type,
            content_encoding=content_encoding,
            elapsed_seconds=clock() - started,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> StaffScheduleClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def build_form_data(query: ScheduleSearchQuery) -> dict[str, str]:
    return _form_fields(
        term=query.term,
        campus=query.campus,
        crn=query.crn,
        subject=query.subject,
        course=query.course,
    )


def build_whole_term_form_data(term: str, campus: str = LIVE_WHOLE_TERM_CAMPUS) -> dict[str, str]:
    """Form fields for a whole-term request: empty subject, CRN and course number."""
    return _form_fields(term=term, campus=campus, crn=None, subject=None, course=None)


def _form_fields(
    *,
    term: str,
    campus: str | None,
    crn: str | None,
    subject: str | None,
    course: str | None,
) -> dict[str, str]:
    return {
        "P_SEMESTER": normalize_banner_term_code(term),
        "P_SESSION": "",
        "P_CAMPUS": (campus or "").strip().upper(),
        "P_COL": "",
        "P_DEPT": "",
        "p_status": "",
        "p_ssts_code": "",
        "P_CRSE_LEVL": "",
        "P_REF": (crn or "").strip(),
        "P_SUBJ": (subject or "").strip().upper(),
        "P_NUM": (course or "").strip().upper(),
        "P_TITLE": "",
        "P_CR": "",
        "P_INSTRUCTOR": "",
        "P_TIME1": "",
        "P_UGR": "",
        "p_insm_x_inad": "YAD",
        "p_insm_x_incl": "YCL",
        "p_insm_x_inhb": "YHB",
        "p_insm_x_inpd": "YPD",
        "p_insm_x_innl": "YNULL",
        "p_insm_x_inot": "YOT",
        "p_day_x": "no_val",
        "p_day": "no_val",
    }
