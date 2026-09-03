import type { RankingMetadata } from "../types/rankings";
import type { RankingFilters } from "../utils/rankings";

interface FilterBarProps {
  filters: RankingFilters;
  metadata: RankingMetadata;
  onFiltersChange: (filters: RankingFilters) => void;
  term: string;
  onTermChange: (term: string) => void;
}

const controlClass =
  "mt-1.5 w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm text-ink shadow-sm transition focus:border-spruce focus:outline-none focus:ring-2 focus:ring-spruce/20";

export function FilterBar({
  filters,
  metadata,
  onFiltersChange,
  term,
  onTermChange,
}: FilterBarProps) {
  const update = <Key extends keyof RankingFilters>(key: Key, value: RankingFilters[Key]) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  return (
    <section
      aria-label="Course ranking filters"
      className="z-20 border-y border-rule bg-paper/95 px-4 py-4 shadow-sm backdrop-blur md:px-6 lg:sticky lg:top-0"
    >
      <div className="mx-auto grid max-w-[1500px] gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        <label className="filter-label">
          Term
          <select className={controlClass} value={term} onChange={(event) => onTermChange(event.target.value)}>
            {metadata.terms.map((item) => (
              <option key={item.term} value={item.term}>{item.term_name} ({item.term})</option>
            ))}
          </select>
        </label>

        <label className="filter-label">
          Subject
          <select className={controlClass} value={filters.subject} onChange={(event) => update("subject", event.target.value)}>
            <option value="">All subjects</option>
            {metadata.subjects.map(({ subject }) => <option key={subject} value={subject}>{subject}</option>)}
          </select>
        </label>

        <label className="filter-label sm:col-span-2">
          Course code
          <input
            aria-describedby="course-search-help"
            autoCapitalize="characters"
            className={controlClass}
            type="search"
            value={filters.courseSearch}
            placeholder="MAC 1105 or 1105"
            onChange={(event) => update("courseSearch", event.target.value)}
          />
          <span className="mt-1 block normal-case tracking-normal text-stone-500" id="course-search-help">Exact subject/course lookup</span>
        </label>

        <label className="filter-label sm:col-span-2 lg:col-span-1">
          GenEd
          <select className={controlClass} value={filters.genedCode} onChange={(event) => update("genedCode", event.target.value)}>
            <option value="">All attributes</option>
            {metadata.genedAttributes.map(({ code, label }) => (
              <option key={`${code}:${label}`} value={code}>{code} — {label}</option>
            ))}
          </select>
        </label>

        <label className="filter-label sm:col-span-2 lg:col-span-1">
          Modality
          <select className={controlClass} value={filters.deliveryMethod} onChange={(event) => update("deliveryMethod", event.target.value)}>
            <option value="">All formats</option>
            {metadata.deliveryMethods.map(({ code, label }) => (
              <option key={code} value={code}>{label ?? "Unknown label"} ({code})</option>
            ))}
          </select>
        </label>

        <label className="filter-label">
          Confidence
          <select className={controlClass} value={filters.confidence} onChange={(event) => update("confidence", event.target.value as RankingFilters["confidence"])}>
            <option value="all">All levels</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>

        <label className="filter-label">
          Sort by
          <select className={controlClass} value={filters.sort} onChange={(event) => update("sort", event.target.value as RankingFilters["sort"])}>
            <option value="easiness_desc">Easiness: high to low</option>
            <option value="easiness_asc">Easiness: low to high</option>
            <option value="withdrawal_asc">W rate: low to high</option>
            <option value="seats_desc">Open seats</option>
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
              aria-valuetext={`${filters.minimumEasiness.toFixed(1)} out of 10`}
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
