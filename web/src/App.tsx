import { useEffect, useMemo, useState } from "react";

import { fetchMetadata, fetchRankings, isUsingMockData } from "./api/rankings";
import { FilterBar } from "./components/FilterBar";
import { RankingTable } from "./components/RankingTable";
import { SYNTHETIC_FIXTURE_NOTICE } from "./fixtures/rankings";
import type {
  MetadataLoader,
  RankingLoader,
  RankingMetadata,
  RankingsSearchResponse,
} from "./types/rankings";
import {
  hasActiveFilters,
  initialFilters,
  parseCourseSearch,
  type RankingFilters,
} from "./utils/rankings";

const PAGE_SIZE = 50;

interface AppProps {
  rankingLoader?: RankingLoader;
  metadataLoader?: MetadataLoader;
  mockMode?: boolean;
}

const newestTerm = (metadata: RankingMetadata): string | null => {
  if (metadata.terms.some(({ term }) => term === "202701")) return "202701";
  return metadata.terms.toSorted((left, right) => right.term.localeCompare(left.term))[0]?.term ?? null;
};

const emptyPage: RankingsSearchResponse = { items: [], total: 0, limit: PAGE_SIZE, offset: 0 };

export default function App({
  rankingLoader = fetchRankings,
  metadataLoader = fetchMetadata,
  mockMode = isUsingMockData,
}: AppProps) {
  const [metadata, setMetadata] = useState<RankingMetadata | null>(null);
  const [metadataLoading, setMetadataLoading] = useState(true);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const [metadataVersion, setMetadataVersion] = useState(0);
  const [term, setTerm] = useState<string | null>(null);
  const [filters, setFilters] = useState<RankingFilters>(initialFilters);
  const [page, setPage] = useState<RankingsSearchResponse>(emptyPage);
  const [offset, setOffset] = useState(0);
  const [rankingsLoading, setRankingsLoading] = useState(false);
  const [rankingsError, setRankingsError] = useState<string | null>(null);
  const [expandedCrn, setExpandedCrn] = useState<string | null>(null);
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setMetadataLoading(true);
    setMetadataError(null);
    metadataLoader(controller.signal)
      .then((result) => {
        setMetadata(result);
        setTerm((current) =>
          current && result.terms.some(({ term: code }) => code === current)
            ? current
            : newestTerm(result),
        );
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setMetadata(null);
          setTerm(null);
          setMetadataError(
            reason instanceof Error ? reason.message : "Unable to load filter metadata.",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setMetadataLoading(false);
      });
    return () => controller.abort();
  }, [metadataLoader, metadataVersion]);

  const query = useMemo(() => {
    if (!term) return null;
    const parsedSearch = parseCourseSearch(filters.courseSearch);
    return {
      term,
      subject: filters.subject || parsedSearch.subject,
      course_number: parsedSearch.courseNumber,
      gened_code: filters.genedCode || undefined,
      delivery_method: filters.deliveryMethod || undefined,
      seats_open: filters.openSeatsOnly || undefined,
      min_easiness: filters.minimumEasiness > 0 ? filters.minimumEasiness : undefined,
      confidence: filters.confidence === "all" ? undefined : filters.confidence,
      sort: filters.sort,
      limit: PAGE_SIZE,
      offset,
    };
  }, [filters, offset, term]);

  useEffect(() => {
    if (!query) return;
    const controller = new AbortController();
    setRankingsLoading(true);
    setRankingsError(null);
    setExpandedCrn(null);
    rankingLoader(query, controller.signal)
      .then((result) => setPage(result))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setPage({ ...emptyPage, offset: query.offset });
          setRankingsError(
            reason instanceof Error ? reason.message : "Unable to load rankings.",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setRankingsLoading(false);
      });
    return () => controller.abort();
  }, [query, rankingLoader, requestVersion]);

  const selectedTerm = metadata?.terms.find(({ term: code }) => code === term);
  const firstShown = page.total === 0 ? 0 : page.offset + 1;
  const lastShown = Math.min(page.offset + page.items.length, page.total);
  const canGoBack = page.offset > 0;
  const canGoForward = page.offset + page.limit < page.total;

  const changeFilters = (nextFilters: RankingFilters) => {
    setFilters(nextFilters);
    setOffset(0);
  };

  const changeTerm = (nextTerm: string) => {
    setTerm(nextTerm);
    setOffset(0);
  };

  const toggleDetails = (crn: string) => {
    setExpandedCrn((current) => (current === crn ? null : crn));
  };

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="border-b border-rule bg-[#faf8f1] px-4 py-6 md:px-6">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <span aria-hidden="true" className="grid size-10 place-items-center rounded-sm bg-spruce font-display text-xl font-black text-white">A</span>
              <p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-spruce">Easy-A Beta · USF Tampa</p>
            </div>
            <h1 className="mt-4 max-w-3xl font-display text-4xl font-bold leading-none tracking-tight text-ink md:text-5xl">Find the section that fits.</h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-stone-600 md:text-base">Compare historical outcomes, current section information, course format, and evidence-backed policy signals in one honest view.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {mockMode ? <span className="rounded-sm border border-brass/50 bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-950">{SYNTHETIC_FIXTURE_NOTICE}</span> : <span className="rounded-sm border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-950">Connected to API</span>}
            <span className="rounded-sm border border-stone-300 bg-white px-3 py-1.5 font-mono text-xs text-stone-600">Beta · rankings preview</span>
          </div>
        </div>
      </header>

      {metadataLoading ? (
        <div className="border-b border-rule bg-white/60 px-4 py-4 text-center text-sm font-semibold text-stone-600" role="status" aria-live="polite">Loading terms and filters…</div>
      ) : null}

      {metadataError ? (
        <section className="mx-auto mt-6 max-w-[1452px] rounded-lg border border-red-200 bg-red-50 p-6" role="alert">
          <h2 className="font-display text-xl font-bold text-red-950">Metadata unavailable</h2>
          <p className="mt-2 text-sm text-red-900">Terms and filter options could not be loaded. {metadataError}</p>
          <button type="button" className="mt-4 rounded-md bg-red-900 px-4 py-2 text-sm font-bold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-900" onClick={() => setMetadataVersion((version) => version + 1)}>Try metadata again</button>
        </section>
      ) : null}

      {!metadataLoading && !metadataError && metadata && metadata.terms.length === 0 ? (
        <section className="mx-auto mt-6 max-w-[1452px] rounded-lg border border-amber-300 bg-amber-50 p-6" role="status">
          <h2 className="font-display text-xl font-bold text-amber-950">No academic terms available</h2>
          <p className="mt-2 text-sm text-amber-900">The API returned no term metadata, so rankings cannot be searched yet.</p>
        </section>
      ) : null}

      {metadata && term ? (
        <FilterBar filters={filters} metadata={metadata} onFiltersChange={changeFilters} term={term} onTermChange={changeTerm} />
      ) : null}

      <main id="main-content" className="mx-auto max-w-[1500px] px-4 py-7 md:px-6 md:py-10" tabIndex={-1}>
        {metadata && term ? (
          <>
            <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="eyebrow">Ranked sections</p>
                <h2 className="mt-1 font-display text-2xl font-bold">{selectedTerm?.term_name ?? term} course index</h2>
              </div>
              {!rankingsLoading && !rankingsError ? <p className="text-sm font-semibold text-stone-600" aria-live="polite">Showing {firstShown}–{lastShown} of {page.total} sections</p> : null}
            </div>

            {rankingsLoading ? (
              <div className="rounded-lg border border-rule bg-white p-8 shadow-ledger" role="status" aria-label="Loading course rankings" aria-live="polite">
                <div className="h-3 w-28 animate-pulse rounded bg-stone-200" />
                <div className="mt-5 space-y-3" aria-hidden="true">{[1, 2, 3, 4].map((item) => <div className="h-14 animate-pulse rounded bg-stone-100" key={item} />)}</div>
                <span className="sr-only">Loading course rankings</span>
              </div>
            ) : null}

            {rankingsError ? (
              <section className="rounded-lg border border-red-200 bg-red-50 p-6" role="alert">
                <h2 className="font-display text-xl font-bold text-red-950">Rankings are unavailable</h2>
                <p className="mt-2 text-sm text-red-900">{rankingsError}</p>
                <button type="button" className="mt-4 rounded-md bg-red-900 px-4 py-2 text-sm font-bold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-900" onClick={() => setRequestVersion((version) => version + 1)}>Try again</button>
              </section>
            ) : null}

            {!rankingsLoading && !rankingsError && page.items.length > 0 ? (
              <>
                <RankingTable rankings={page.items} rankOffset={page.offset} expandedCrn={expandedCrn} onToggle={toggleDetails} />
                <nav aria-label="Course results pages" className="mt-5 flex items-center justify-between gap-4 border-t border-rule pt-5">
                  <button type="button" className="rounded-md border border-stone-300 bg-white px-4 py-2 text-sm font-bold text-ink disabled:cursor-not-allowed disabled:opacity-45 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-spruce" disabled={!canGoBack} onClick={() => setOffset((current) => Math.max(0, current - page.limit))}>Previous</button>
                  <span className="text-center text-xs font-semibold text-stone-600" aria-live="polite">Showing {firstShown}–{lastShown} of {page.total} sections</span>
                  <button type="button" className="rounded-md border border-stone-300 bg-white px-4 py-2 text-sm font-bold text-ink disabled:cursor-not-allowed disabled:opacity-45 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-spruce" disabled={!canGoForward} onClick={() => setOffset((current) => current + page.limit)}>Next</button>
                </nav>
              </>
            ) : null}

            {!rankingsLoading && !rankingsError && page.items.length === 0 ? (
              <section className="rounded-lg border border-dashed border-stone-400 bg-white/60 p-10 text-center" role="status">
                <h2 className="font-display text-2xl font-bold">{hasActiveFilters(filters) ? "No sections match these filters" : `No sections available for ${selectedTerm?.term_name ?? term}`}</h2>
                <p className="mt-2 text-sm text-stone-600">{hasActiveFilters(filters) ? "Try clearing the course code or widening confidence, modality, seat, or GenEd filters." : "This term is listed by the API but has no searchable section data."}</p>
                {hasActiveFilters(filters) ? <button type="button" className="mt-5 rounded-md bg-spruce px-4 py-2 text-sm font-bold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-spruce" onClick={() => changeFilters(initialFilters)}>Reset filters</button> : null}
              </section>
            ) : null}
          </>
        ) : null}
      </main>

      <footer className="border-t border-rule px-4 py-6 text-xs leading-relaxed text-stone-600">
        <details className="mx-auto max-w-3xl rounded-md bg-white/50 px-4 py-3">
          <summary className="cursor-pointer font-bold text-spruce focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-spruce">About Easy-A Beta</summary>
          <ul className="mt-3 list-disc space-y-1 pl-5">
            <li>Rankings use historical aggregate outcomes; scores are estimates, not guarantees.</li>
            <li>Current seat counts and instructor assignments can change.</li>
            <li>Historical syllabus policies may differ from the current term.</li>
            <li>USF ODS approved use of aggregate InfoCenter grade-distribution data for this project; this does not imply USF endorsement of Easy-A.</li>
          </ul>
        </details>
      </footer>
    </div>
  );
}
