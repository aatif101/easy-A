import { useState } from "react";

import { CopyCrnButton } from "../components/CopyCrnButton";
import { GradeBar, GradeLegend } from "../components/GradeBar";
import { SearchBox } from "../components/SearchBox";
import { LoadError, Loading } from "../components/Status";
import { loadAllSections } from "../lib/loadAll";
import { inAppClick, type Route } from "../lib/route";
import { GEN_ED_AREAS } from "../lib/search";
import { formatShare, toSectionView, type SectionView } from "../lib/section";
import { useLoad } from "../lib/useLoad";
import type { RankingLoader, SectionRanking } from "../types/rankings";

const SHOWN = 8;

interface HomePageProps {
  term: string;
  rankingLoader: RankingLoader;
  navigate: (route: Route) => void;
}

export function HomePage({ term, rankingLoader, navigate }: HomePageProps) {
  const [areaId, setAreaId] = useState("social-sciences");
  const area = GEN_ED_AREAS.find((item) => item.id === areaId) ?? GEN_ED_AREAS[0];
  const [state, retry] = useLoad(`${term}:${area.id}`, (signal) =>
    loadAllSections(rankingLoader, area.codes.map((code) => ({ term, gened_code: code })), signal),
  );

  // Only sections whose own instructor has enough history, highest A share first.
  // One row per instructor and course: several sections by the same person share one A rate.
  const rows: { ranking: SectionRanking; view: SectionView; crns: string[] }[] = [];
  if (state.status === "ready") {
    for (const ranking of state.data) {
      const view = toSectionView(ranking);
      if (view.kind !== "instructor") continue;
      const existing = rows.find(
        (row) =>
          row.view.instructor === view.instructor &&
          row.ranking.subject === ranking.subject &&
          row.ranking.course_number === ranking.course_number,
      );
      if (existing) existing.crns.push(ranking.crn);
      else rows.push({ ranking, view, crns: [ranking.crn] });
    }
    rows.sort((left, right) => (right.view.aShare ?? 0) - (left.view.aShare ?? 0));
    rows.splice(SHOWN);
  }
  const label = area.label;
  const areaRoute: Route = { view: "gened", area: area.id };

  return (
    <>
      <h1 className="mb-4 text-[28px] font-semibold leading-tight" style={{ textWrap: "balance" }}>
        Who gives the most A's?
      </h1>
      <div className="max-w-3xl">
        <SearchBox onSearch={(q) => navigate({ view: "search", q })} />
        <p className="mt-2 text-sm text-slate">Search a CRN, course code or number, title, subject, or professor’s listed name. Try ENC 1101, 2045L, Program Design, or calculus 1.</p>
      </div>

      <section className="mt-12" aria-labelledby="top-heading">
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="top-heading" className="text-lg font-semibold">
            {label} sections with high A rates
          </h2>
          <span className="text-[13px] text-slate">Instructor's past grades in that course</span>
        </div>

        <div role="group" aria-label="Gen Ed requirement" className="mb-3 flex flex-wrap gap-1.5">
          {GEN_ED_AREAS.map((item) => {
            const on = item.id === area.id;
            return (
              <button
                key={item.id}
                type="button"
                aria-pressed={on}
                onClick={() => setAreaId(item.id)}
                className={`h-9 rounded-full border px-3.5 text-sm font-medium ${
                  on ? "border-ink bg-ink text-white" : "border-silver bg-white text-ink hover:bg-wash"
                }`}
              >
                {item.label}
              </button>
            );
          })}
        </div>

        {state.status === "loading" ? <Loading label={`Loading ${label} sections…`} /> : null}
        {state.status === "error" ? <LoadError onRetry={retry} /> : null}
        {state.status === "ready" && rows.length === 0 ? (
          <p className="rounded-lg border border-line px-4 py-5 text-sm text-slate">
            No {label} sections have enough instructor history yet.{" "}
            <a href={`?gened=${area.id}`} onClick={inAppClick(navigate, areaRoute)}>
              See all {label} sections
            </a>
          </p>
        ) : null}

        {rows.length > 0 ? (
          <>
            <div className="overflow-hidden rounded-lg border border-line">
            <div aria-hidden="true" className="hidden grid-cols-[64px_170px_minmax(0,1.3fr)_minmax(0,1fr)_120px] gap-4 bg-wash px-3.5 py-2.5 text-sm text-slate min-[760px]:grid">
              <span>A%</span>
              <span className="flex items-center gap-2">Grades <GradeLegend /></span>
              <span>Course</span>
              <span>Instructor</span>
              <span>CRNs</span>
            </div>
            <ol className="flex flex-col">
              {rows.map(({ ranking, view, crns }) => (
                <li
                  key={ranking.crn}
                  className="grid grid-cols-[56px_minmax(0,1fr)] items-center gap-x-4 gap-y-1.5 border-t border-line px-3.5 py-3 text-sm first:border-t-0 min-[760px]:grid-cols-[64px_170px_minmax(0,1.3fr)_minmax(0,1fr)_120px]"
                >
                  <span className="tabular row-span-2 text-lg font-bold min-[760px]:row-span-1">{formatShare(view.aShare ?? 0)}</span>
                  <span className="flex flex-col gap-1">
                    <GradeBar share={view.aShare ?? 0} />
                    <span className="tabular text-xs text-slate">{view.caption}</span>
                  </span>
                  <span className="min-w-0">
                    <a
                      href={`?q=${encodeURIComponent(`${ranking.subject} ${ranking.course_number}`)}`}
                      onClick={inAppClick(navigate, { view: "search", q: `${ranking.subject} ${ranking.course_number}` })}
                      className="font-semibold text-ink no-underline hover:underline"
                    >
                      {ranking.subject} {ranking.course_number}
                    </a>
                    <span className="block truncate text-[13px] text-slate" title={ranking.course_title}>
                      {ranking.course_title}
                    </span>
                  </span>
                  <span className="col-start-2 min-[760px]:col-start-auto">{view.instructor}</span>
                  <span className="col-start-2 flex flex-wrap gap-x-4 gap-y-1.5 min-[760px]:col-start-auto min-[760px]:flex-col">
                    {crns.slice(0, 2).map((crn) => (
                      <span key={crn} className="flex items-center gap-2">
                        <span className="font-mono">{crn}</span>
                        <CopyCrnButton crn={crn} />
                      </span>
                    ))}
                    {crns.length > 2 ? (
                      <a
                        href={`?q=${encodeURIComponent(`${ranking.subject} ${ranking.course_number}`)}`}
                        onClick={inAppClick(navigate, { view: "search", q: `${ranking.subject} ${ranking.course_number}` })}
                        className="text-xs font-semibold"
                      >
                        +{crns.length - 2} more sections
                      </a>
                    ) : null}
                  </span>
                </li>
              ))}
            </ol>
            </div>
            <a
              href={`?gened=${area.id}`}
              onClick={inAppClick(navigate, areaRoute)}
              className="mt-3 inline-block text-sm font-semibold"
            >
              All {label} sections
            </a>
          </>
        ) : null}
      </section>
    </>
  );
}
