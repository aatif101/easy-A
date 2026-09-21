from typing import TYPE_CHECKING, Any

from easy_a.rankings.models import (
    GenEdAttribute,
    HistoricalAnalyticsSummary,
    ModalityInfo,
    RankingFreshness,
    RankingProvenance,
    RankingSignal,
    SeatInfo,
    SectionRanking,
)

# The service layer is imported lazily. easy_a.models.__init__ imports
# easy_a.rankings.cache (SectionRankingCache), which runs this package __init__;
# eagerly importing easy_a.rankings.service here dragged the heavy analytics /
# instructors / signals chain into every `import easy_a.models`, creating a
# circular import. Deferring the service exports until first access keeps the
# model import lightweight while preserving the public `easy_a.rankings` API.
if TYPE_CHECKING:
    from easy_a.rankings.service import (
        RankingResolutionError,
        rank_course_sections,
        rank_section,
    )

_LAZY_SERVICE_EXPORTS = {
    "RankingResolutionError",
    "rank_course_sections",
    "rank_section",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_SERVICE_EXPORTS:
        from easy_a.rankings import service

        return getattr(service, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "GenEdAttribute",
    "HistoricalAnalyticsSummary",
    "ModalityInfo",
    "RankingFreshness",
    "RankingProvenance",
    "RankingResolutionError",
    "RankingSignal",
    "SectionRanking",
    "SeatInfo",
    "rank_course_sections",
    "rank_section",
]
