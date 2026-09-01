from __future__ import annotations

from dataclasses import dataclass

import httpx

BASE_URL = "https://usfweb.usf.edu"
RESULTS_PATH = "/DSS/StaffScheduleSearch/StaffSearch/Results"
DEFAULT_USER_AGENT = "Easy-A data pipeline (https://github.com/aatif101/easy-A)"


@dataclass(frozen=True)
class ScheduleSearchQuery:
    term: str
    campus: str | None = None
    subject: str | None = None
    course: str | None = None
    crn: str | None = None

    def __post_init__(self) -> None:
        normalize_banner_term_code(self.term)
        if self.crn is None and self.subject is None:
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

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> StaffScheduleClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def build_form_data(query: ScheduleSearchQuery) -> dict[str, str]:
    return {
        "P_SEMESTER": normalize_banner_term_code(query.term),
        "P_SESSION": "",
        "P_CAMPUS": (query.campus or "").strip().upper(),
        "P_COL": "",
        "P_DEPT": "",
        "p_status": "",
        "p_ssts_code": "",
        "P_CRSE_LEVL": "",
        "P_REF": (query.crn or "").strip(),
        "P_SUBJ": (query.subject or "").strip().upper(),
        "P_NUM": (query.course or "").strip().upper(),
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


def normalize_banner_term_code(value: str | int) -> str:
    """Validate the six-digit Banner term without owning Developer 1's term model."""
    term_code = str(value).strip()
    if len(term_code) != 6 or not term_code.isdigit():
        raise ValueError(f"Banner term code must be six digits, got {value!r}.")
    return term_code
