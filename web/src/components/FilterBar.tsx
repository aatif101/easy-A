import type { Dispatch, SetStateAction } from "react";

import type { RankingFilters } from "../utils/rankings";

interface FilterBarProps {
  filters: RankingFilters;
  setFilters: Dispatch<SetStateAction<RankingFilters>>;
  term: string;
  setTerm: (term: string) => void;
}

const selectClass =
  "mt-1.5 w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm text-ink shadow-sm transition focus:border-spruce focus:outline-none focus:ring-2 focus:ring-spruce/20";

export function FilterBar({ filters, setFilters, term, setTerm }: FilterBarProps) {
  const update = <Key extends keyof RankingFilters>(key: Key, value: RankingFilters[Key]) => {
    setFilters((current) => ({ ...current, [key]: value }));
  };

  return (
    <section
      aria-label="Course ranking filters"
      className="sticky top-0 z-20 border-y border-rule bg-paper/95 px-4 py-4 shadow-sm backdrop-blur md:px-6"
    >
      <div className="mx-auto grid max-w-[1500px] gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        <label className="filter-label">
          Term
          <select className={selectClass} value={term} onChange={(event) => setTerm(event.target.value)}>
            <option value="202701">Spring 2027</option>
            <option value="202608">Fall 2026</option>
          </select>
        </label>

        <label className="filter-label sm:col-span-2">
          Subject or course
          <input
            className={selectClass}
            type="search"
            value={filters.search}
            placeholder="Try MAC 1105 or College Algebra"
            onChange={(event) => update("search", event.target.value)}
          />
        </label>

        <label className="filter-label">
          GenEd
          <select className={selectClass} value={filters.gened} onChange={(event) => update("gened", event.target.value as RankingFilters["gened"])}>
            <option value="all">All courses</option>
            <option value="yes">GenEd only</option>
            <option value="no">Not GenEd</option>
          </select>
        </label>

        <label className="filter-label">
          Modality
          <select className={selectClass} value={filters.modality} onChange={(event) => update("modality", event.target.value as RankingFilters["modality"])}>
            <option value="all">All formats</option>
            <option value="classroom">Classroom</option>
            <option value="hybrid">Hybrid</option>
            <option value="online">Online</option>
          </select>
        </label>

        <label className="filter-label">
          Confidence
          <select className={selectClass} value={filters.confidence} onChange={(event) => update("confidence", event.target.value as RankingFilters["confidence"])}>
            <option value="all">All levels</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>

        <label className="filter-label">
          Sort by
          <select className={selectClass} value={filters.sort} onChange={(event) => update("sort", event.target.value as RankingFilters["sort"])}>
            <option value="easiness">Easiness: high to low</option>
            <option value="withdrawal">W rate: low to high</option>
            <option value="seats">Open seats</option>
            <option value="course">Course code</option>
          </select>
        </label>

        <div className="flex flex-col justify-between gap-3 sm:col-span-2 lg:col-span-4 xl:col-span-8 xl:flex-row xl:items-center">
          <label className="flex min-w-64 items-center gap-3 text-sm font-semibold text-ink">
            <input
              className="size-4 rounded border-stone-400 text-spruce focus:ring-spruce"
              type="checkbox"
              checked={filters.openSeatsOnly}
              onChange={(event) => update("openSeatsOnly", event.target.checked)}
            />
            Open seats only
          </label>
          <label className="flex w-full items-center gap-3 text-sm font-semibold text-ink xl:max-w-md">
            <span className="whitespace-nowrap">Minimum easiness</span>
            <input
              className="h-2 w-full accent-spruce"
              type="range"
              min="0"
              max="10"
              step="0.5"
              value={filters.minimumEasiness}
              onChange={(event) => update("minimumEasiness", Number(event.target.value))}
            />
            <output className="w-14 font-mono text-xs">{filters.minimumEasiness.toFixed(1)}</output>
          </label>
        </div>
      </div>
    </section>
  );
}
