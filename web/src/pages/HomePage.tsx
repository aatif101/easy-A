import { useEffect, useId, useRef, useState } from "react";

import { SearchBox } from "../components/SearchBox";
import { SectionTable } from "../components/SectionTable";
import { LoadError, Loading } from "../components/Status";
import { loadAllSections } from "../lib/loadAll";
import { inAppClick, type Route } from "../lib/route";
import { GEN_ED_AREAS } from "../lib/search";
import { termName, toSectionView, type SectionRow } from "../lib/section";
import { useLoad } from "../lib/useLoad";
import type { RankingLoader } from "../types/rankings";

const SHOWN = 8;
const MAX_PER_INSTRUCTOR = 2;
const DEFAULT_AREA = "social-sciences";

interface HomePageProps {
  term: string;
  rankingLoader: RankingLoader;
  navigate: (route: Route) => void;
}

export function HomePage({ term, rankingLoader, navigate }: HomePageProps) {
  const [areaId, setAreaId] = useState(DEFAULT_AREA);
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const popoverId = useId();

  useEffect(() => {
    if (!open) return;
    popoverRef.current?.querySelector<HTMLButtonElement>('[aria-pressed="true"]')?.focus();
    const dismissOutside = (event: MouseEvent) => {
      if (event.target instanceof Node && !buttonRef.current?.contains(event.target) && !popoverRef.current?.contains(event.target)) {
        setOpen(false);
      }
    };
    const dismissWithEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", dismissOutside);
    document.addEventListener("keydown", dismissWithEscape);
    return () => {
      document.removeEventListener("mousedown", dismissOutside);
      document.removeEventListener("keydown", dismissWithEscape);
    };
  }, [open]);

  const selectArea = (id: string) => {
    setAreaId(id);
    setOpen(false);
    buttonRef.current?.focus();
  };
  const area = GEN_ED_AREAS.find((item) => item.id === areaId) ?? GEN_ED_AREAS[0];
  const [state, retry] = useLoad(`${term}:${area.id}`, (signal) =>
    loadAllSections(rankingLoader, area.codes.map((code) => ({ term, gened_code: code })), signal),
  );

  // Only sections whose own instructor has enough history, highest A share first. Several sections
  // by one person share one A rate, so a cap keeps them from filling the whole list.
  const rows: SectionRow[] = [];
  if (state.status === "ready") {
    const known = state.data
      .map((ranking) => ({ ranking, view: toSectionView(ranking) }))
      .filter(({ view }) => view.kind === "instructor")
      .toSorted((left, right) => (right.view.aShare ?? 0) - (left.view.aShare ?? 0) || left.ranking.crn.localeCompare(right.ranking.crn));
    const perInstructor = new Map<string, number>();
    for (const row of known) {
      if (rows.length === SHOWN) break;
      const key = `${row.view.instructor}|${row.ranking.subject}|${row.ranking.course_number}`;
      const count = perInstructor.get(key) ?? 0;
      if (count === MAX_PER_INSTRUCTOR) continue;
      perInstructor.set(key, count + 1);
      rows.push(row);
    }
  }
  const label = area.label;
  const areaRoute: Route = { view: "gened", area: area.id };

  return (
    <>
      <h1 className="mb-4 text-[28px] font-semibold leading-tight" style={{ textWrap: "balance" }}>
        Find your {termName(term)} classes
      </h1>
      <div className="relative max-w-3xl">
        <SearchBox
          onSearch={(q) => navigate({ view: "search", q })}
          rightButton={
            <button
              ref={buttonRef}
              type="button"
              aria-label="GenEd filters"
              aria-haspopup="dialog"
              aria-expanded={open}
              aria-controls={open ? popoverId : undefined}
              onClick={() => setOpen((value) => !value)}
              className={`relative h-[52px] w-10 shrink-0 rounded-lg border border-silver text-xl text-ink hover:bg-wash ${areaId !== DEFAULT_AREA ? "bg-wash" : "bg-white"}`}
            >
              <span aria-hidden="true">⋮</span>
              {areaId !== DEFAULT_AREA ? <span aria-hidden="true" className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-green" /> : null}
            </button>
          }
        />
        {open ? (
          <div
            ref={popoverRef}
            id={popoverId}
            role="dialog"
            aria-label="GenEd filters"
            className="absolute right-0 top-[60px] z-20 flex max-h-[60vh] w-64 max-w-full flex-col gap-2 overflow-y-auto rounded-lg border border-line bg-white p-3 shadow-lg"
          >
            {GEN_ED_AREAS.map((item) => (
              <button
                key={item.id}
                type="button"
                aria-pressed={item.id === area.id}
                onClick={() => selectArea(item.id)}
                className={`rounded-lg border px-3 py-2 text-left text-sm font-medium ${item.id === area.id ? "border-ink bg-ink text-white" : "border-silver bg-white text-ink hover:bg-wash"}`}
              >
                {item.label}
              </button>
            ))}
            <button type="button" onClick={() => selectArea(DEFAULT_AREA)} className="rounded-lg px-3 py-2 text-left text-sm text-slate hover:bg-wash">
              Clear filters
            </button>
          </div>
        ) : null}
        <p className="mt-2 text-sm text-slate">Search a CRN, course code or number, title, subject, or professor’s listed name. Try ENC 1101, 2045L, Program Design, or calculus 1.</p>
      </div>

      <section className="mt-12" aria-labelledby="top-heading">
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="top-heading" className="text-lg font-semibold">
            {label} sections with high A rates
          </h2>
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
            <SectionTable
              rows={rows}
              onOpenCourse={(subject, courseNumber) => navigate({ view: "search", q: `${subject} ${courseNumber}` })}
            />
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
