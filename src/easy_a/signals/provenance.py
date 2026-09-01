from __future__ import annotations

MAX_EVIDENCE_LENGTH = 240


def evidence_window(text: str, start: int, end: int) -> str:
    left_bound = max(0, start - MAX_EVIDENCE_LENGTH // 2)
    right_bound = min(len(text), end + MAX_EVIDENCE_LENGTH // 2)
    left = max(text.rfind(".", left_bound, start), text.rfind("\n", left_bound, start))
    right_candidates = [
        position
        for marker in (".", "\n")
        if (position := text.find(marker, end, right_bound)) >= 0
    ]
    window_start = left + 1 if left >= 0 else left_bound
    window_end = min(right_candidates) + 1 if right_candidates else right_bound
    excerpt = text[window_start:window_end].strip()
    return excerpt[:MAX_EVIDENCE_LENGTH].rstrip()
