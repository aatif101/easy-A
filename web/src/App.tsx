import { useEffect, useMemo, useState } from "react";

import { fetchRankings, isUsingMockData } from "./api/rankings";
import { FilterBar } from "./components/FilterBar";
import { RankingTable } from "./components/RankingTable";
import { SYNTHETIC_FIXTURE_NOTICE } from "./fixtures/rankings";
import type { RankingLoader, SectionRanking } from "./types/rankings";
import { filterAndSortRankings, initialFilters, type RankingFilters } from "./utils/rankings";

interface AppProps {
  loader?: RankingLoader;
  mockMode?: boolean;
}

export default function App({ loader = fetchRankings, mockMode = isUsingMockData }: AppProps) {
  const [term, setTerm] = useState("202701");
  const [filters, setFilters] = useState<RankingFilters>(initialFilters);
  const [rankings, setRankings] = useState<SectionRanking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedCrn, setExpandedCrn] = useState<string | null>(null);
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setExpandedCrn(null);
    loader({ term }, controller.signal)
      .then((results) => setRankings(results))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "Unable to load rankings.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [loader, requestVersion, term]);

  const visibleRankings = useMemo(
    () => filterAndSortRankings(rankings, filters),
    [filters, rankings],
  );
  const termName = rankings[0]?.term_name ?? (term === "202608" ? "Fall 2026" : "Spring 2027");

  const toggleDetails = (crn: string) => {
    setExpandedCrn((current) => (current === crn ? null : crn));
  };

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="border-b border-rule bg-[#faf8f1] px-4 py-6 md:px-6">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <span aria-hidden="true" className="grid size-10 place-items-center rounded-sm bg-spruce font-display text-xl font-black text-white">A</span>
              <p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-spruce">Easy-A · USF Tampa</p>
            </div>
            <h1 className="mt-4 max-w-3xl font-display text-4xl font-bold leading-none tracking-tight text-ink md:text-5xl">Find the section that fits.</h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-stone-600 md:text-base">Compare historical outcomes, current seats, course format, and evidence-backed policy signals in one honest view.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {mockMode ? <span className="rounded-sm border border-brass/50 bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-950">{SYNTHETIC_FIXTURE_NOTICE}</span> : <span className="rounded-sm border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-950">Connected to API</span>}
            <span className="rounded-sm border border-stone-300 bg-white px-3 py-1.5 font-mono text-xs text-stone-600">V1 · rankings preview</span>
          </div>
        </div>
      </header>

      <FilterBar filters={filters} setFilters={setFilters} term={term} setTerm={setTerm} />

      <main id="main-content" className="mx-auto max-w-[1500px] px-4 py-7 md:px-6 md:py-10" tabIndex={-1}>
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="eyebrow">Ranked sections</p>
            <h2 className="mt-1 font-display text-2xl font-bold">{termName} course index</h2>
          </div>
          {!loading && !error ? <p className="text-sm font-semibold text-stone-600" aria-live="polite">Showing {visibleRankings.length} of {rankings.length} sections</p> : null}
        </div>

        {loading ? (
          <div className="rounded-lg border border-rule bg-white p-8 shadow-ledger" role="status" aria-label="Loading course rankings" aria-live="polite">
            <div className="h-3 w-28 animate-pulse rounded bg-stone-200" />
            <div className="mt-5 space-y-3" aria-hidden="true">{[1, 2, 3, 4].map((item) => <div className="h-14 animate-pulse rounded bg-stone-100" key={item} />)}</div>
            <span className="sr-only">Loading course rankings</span>
          </div>
        ) : null}

        {error ? (
          <section className="rounded-lg border border-red-200 bg-red-50 p-6" role="alert">
            <p className="font-display text-xl font-bold text-red-950">Rankings are unavailable</p>
            <p className="mt-2 text-sm text-red-900">{error}</p>
            <button type="button" className="mt-4 rounded-md bg-red-900 px-4 py-2 text-sm font-bold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-900" onClick={() => setRequestVersion((version) => version + 1)}>Try again</button>
          </section>
        ) : null}

        {!loading && !error && visibleRankings.length ? (
          <RankingTable rankings={visibleRankings} expandedCrn={expandedCrn} onToggle={toggleDetails} />
        ) : null}

        {!loading && !error && visibleRankings.length === 0 ? (
          <section className="rounded-lg border border-dashed border-stone-400 bg-white/60 p-10 text-center">
            <h2 className="font-display text-2xl font-bold">No sections match these filters</h2>
            <p className="mt-2 text-sm text-stone-600">Try widening confidence, modality, or seat availability.</p>
            <button type="button" className="mt-5 rounded-md bg-spruce px-4 py-2 text-sm font-bold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-spruce" onClick={() => setFilters(initialFilters)}>Reset filters</button>
          </section>
        ) : null}
      </main>

      <footer className="border-t border-rule px-4 py-6 text-center text-xs leading-relaxed text-stone-500">
        Easiness is based on historical outcomes and withdrawal rates—not a promise about difficulty.
      </footer>
    </div>
  );
}
