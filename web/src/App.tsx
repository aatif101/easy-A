import { useCallback, useEffect, useState } from "react";

import { fetchRankings, fetchSection, fetchSyncStatus, fetchTerms, isUsingMockData } from "./api/rankings";
import usfBull from "./assets/usf-bull.svg";
import { SearchBox } from "./components/SearchBox";
import { LoadError, Loading } from "./components/Status";
import { SYNTHETIC_FIXTURE_NOTICE } from "./fixtures/rankings";
import { inAppClick, readRoute, routeHref, type Route } from "./lib/route";
import { useLoad } from "./lib/useLoad";
import { HomePage } from "./pages/HomePage";
import { GenEdResults, SearchResults } from "./pages/ResultsPage";
import type { RankingLoader, SectionLoader, SyncStatusLoader, TermsLoader } from "./types/rankings";

interface AppProps {
  rankingLoader?: RankingLoader;
  sectionLoader?: SectionLoader;
  termsLoader?: TermsLoader;
  syncStatusLoader?: SyncStatusLoader;
  mockMode?: boolean;
}

const minutesAgo = (iso: string): string => {
  const minutes = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60_000));
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  return hours < 48 ? `${hours} h ago` : `${Math.round(hours / 24)} days ago`;
};

export default function App({
  rankingLoader = fetchRankings,
  sectionLoader = fetchSection,
  termsLoader = fetchTerms,
  syncStatusLoader = fetchSyncStatus,
  mockMode = isUsingMockData,
}: AppProps) {
  const [route, setRoute] = useState<Route>(() => readRoute(window.location.search));

  useEffect(() => {
    const onPop = () => setRoute(readRoute(window.location.search));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const navigate = useCallback((next: Route) => {
    window.history.pushState(null, "", routeHref(next));
    setRoute(next);
    window.scrollTo({ top: 0 });
  }, []);

  const [terms, retryTerms] = useLoad("terms", (signal) => termsLoader(signal));
  const term =
    terms.status === "ready"
      ? terms.data.map(({ term: code }) => code).toSorted().at(-1) ?? null
      : null;
  const termName = terms.status === "ready" ? terms.data.find((item) => item.term === term)?.term_name ?? term : null;
  const [sync] = useLoad(term && !mockMode ? `sync:${term}` : null, (signal) => syncStatusLoader(term ?? "", signal));

  const loaders = { rankingLoader, sectionLoader, navigate };
  const searchValue = route.view === "search" ? route.q : "";

  return (
    <div className="min-h-screen bg-white text-ink">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-[1240px] flex-wrap items-center gap-4 px-6 py-3">
          <a
            href={window.location.pathname}
            onClick={inAppClick(navigate, { view: "home" })}
            className="inline-flex shrink-0 items-center gap-2.5 whitespace-nowrap text-xl font-bold tracking-[-0.01em] text-ink no-underline"
            aria-label="Easy-A home"
          >
            <img src={usfBull} alt="USF Bull logo" width={56} height={56} className="h-7 w-7 shrink-0 object-contain sm:h-8 sm:w-8" />
            <span>easy<span className="text-green">A</span></span>
          </a>
          {route.view !== "home" ? (
            <div className="order-3 w-full min-[720px]:order-none min-[720px]:w-auto min-[720px]:max-w-[560px] min-[720px]:flex-1">
              <SearchBox size="compact" initialValue={searchValue} onSearch={(q) => navigate({ view: "search", q })} />
            </div>
          ) : null}
          <span className="ml-auto text-sm text-slate">{termName ? `${termName} · Tampa` : "USF Tampa"}</span>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-[1240px] px-6 pb-16 pt-8">
        {mockMode ? (
          <p role="status" className="mb-4 rounded-md border border-line bg-wash px-3 py-2 text-sm">
            {SYNTHETIC_FIXTURE_NOTICE}
          </p>
        ) : null}
        {terms.status === "loading" ? <Loading label="Loading…" /> : null}
        {terms.status === "error" ? <LoadError onRetry={retryTerms} /> : null}
        {term ? (
          route.view === "home" ? (
            <HomePage term={term} rankingLoader={rankingLoader} navigate={navigate} />
          ) : route.view === "search" ? (
            <SearchResults key={route.q} term={term} q={route.q} {...loaders} />
          ) : (
            <GenEdResults key={route.area} term={term} area={route.area} {...loaders} />
          )
        ) : null}
      </main>

      <footer className="mx-auto max-w-[1240px] border-t border-line px-6 pb-10 pt-5 text-[13px] text-slate">
        <p>
          Grades from USF InfoCenter reports, Fall 2024–Spring 2026. Past grades describe past classes, not yours.
          {sync.status === "ready" && sync.data.last_success_at
            ? ` Seats checked ${minutesAgo(sync.data.last_success_at)}; confirm in OASIS.`
            : " Confirm seats in OASIS."}
        </p>
        <p className="mt-1">Independent student project. Not affiliated with the University of South Florida.</p>
      </footer>
    </div>
  );
}
