import { useState } from "react";

import { RmpLink } from "../components/RmpLink";
import { SectionsView } from "../components/SectionsView";
import { LoadError, Loading, Notice } from "../components/Status";
import { loadAllSections } from "../lib/loadAll";
import type { Route } from "../lib/route";
import { formatShare, termSpan } from "../lib/section";
import { useLoad } from "../lib/useLoad";
import type { RankingLoader, RankingQuery } from "../types/rankings";
import type { DiscoveryLoader, DiscoveryResponse, HistoryLoader } from "../types/search";

function Pagination({ offset, total, onPage }: { offset: number; total: number; onPage: (offset: number) => void }) {
  return <div className="mt-4 flex flex-wrap items-center gap-3">
    <button className="rounded border border-silver px-3 py-2 disabled:opacity-40" disabled={offset === 0} onClick={() => onPage(Math.max(0, offset - 20))}>Previous results</button>
    <span className="text-sm text-slate" role="status">{total ? `${offset + 1}–${Math.min(offset + 20, total)} of ${total}` : "0 results"}</span>
    <button className="rounded border border-silver px-3 py-2 disabled:opacity-40" disabled={offset + 20 >= total} onClick={() => onPage(offset + 20)}>Next results</button>
  </div>;
}

export function HistoryPanel({ term, courseId, name, historyLoader }: { term: string; courseId: number; name: string | null; historyLoader: HistoryLoader }) {
  const [offset, setOffset] = useState(0);
  const [state, retry] = useLoad(`${term}:${courseId}:${name}:${offset}`, signal => historyLoader(term, courseId, name, offset, signal));
  if (state.status === "loading") return <Loading label="Loading recorded grades…" />;
  if (state.status === "error") return <LoadError onRetry={retry} message="Unable to load grade history. Check your connection and try again." />;
  const data = state.data;
  return <div className="mt-3 min-w-0 space-y-3 rounded border border-line bg-wash p-3 text-sm">
    <h3 className="font-semibold">Historical grades · {data.course.subject} {data.course.course_number}{name ? ` · ${name}` : ""}</h3>
    {data.status === "unavailable" ? <p>No attributable grade history is available. Missing or ambiguous assignments cannot establish professor history; missing or suppressed source rows cannot be reconstructed.</p> : data.a_share === null ? <p>No letter-grade history — no A share is available.</p> : <p><strong>{formatShare(data.a_share)} A</strong> · {data.observed_grade_count.toLocaleString("en-US")} observed A–F grades{data.status === "insufficient" ? " · too few to trust" : ""} · {data.terms.length} covered {data.terms.length === 1 ? "term" : "terms"}</p>}
    {data.terms.length ? <p>Covered terms: {data.terms.map(t => termSpan(t, t)).join(", ")}</p> : null}
    {data.total > 0 ? <p>Stored distribution: {Object.entries(data.counts).map(([bucket, n]) => `${bucket.toUpperCase()}: ${n}`).join(" · ")}</p> : null}
    <p className="text-slate">Source: stored USF InfoCenter grade reports; instructor attribution uses the USF class schedule. % A is A / observed A–F grades. Laboratory sections are excluded from professor history. USF lists one instructor per section; co-taught courses are attributed to the listed instructor. Past grades describe past classes, not yours.</p>
    {name ? <p className="text-slate">{data.identity_note}</p> : null}
    <ul className="space-y-2">{data.items.map(row => <li key={`${row.term}:${row.crn}:${row.source}`} className="break-words border-t border-line pt-2">
      <p>Historical record · {termSpan(row.term, row.term)} · CRN {row.crn}</p>
      <p>{Object.entries(row.counts).map(([bucket, n]) => `${bucket.toUpperCase()}: ${n}`).join(" · ")}</p>
      <p className="text-xs text-slate">Source: {row.source} · Imported {new Date(row.ingested_at).toLocaleDateString("en-US", { timeZone: "America/New_York" })}</p>
    </li>)}</ul>
    {data.total > 20 ? <Pagination offset={offset} total={data.total} onPage={setOffset} /> : null}
  </div>;
}

/** One query per offered match. A matched course already covers its instructors' sections. */
const sectionFilters = (term: string, data: DiscoveryResponse): Omit<RankingQuery, "limit" | "offset">[] => {
  const courses = data.courses.filter(course => course.current_sections > 0);
  const covered = new Set(courses.map(course => course.course_id));
  return [
    ...courses.map(course => ({ term, subject: course.subject, course_number: course.course_number })),
    ...data.instructors
      .filter(match => match.current_sections > 0 && !covered.has(match.course_id))
      .map(match => ({ term, subject: match.subject, course_number: match.course_number, course_id: match.course_id, instructor: match.name })),
  ];
};

function MatchedSections({ term, q, offset, data, rankingLoader, navigate }: {
  term: string; q: string; offset: number; data: DiscoveryResponse; rankingLoader: RankingLoader; navigate: (route: Route) => void;
}) {
  const filters = sectionFilters(term, data);
  const [state, retry] = useLoad(`${term}:${q}:${offset}:sections`, signal => loadAllSections(rankingLoader, filters, signal));
  if (filters.length === 0) return <Notice title={`Nothing matching "${q}" is offered in ${termSpan(term, term)}`}>Past grades for these matches are below.</Notice>;
  if (state.status === "loading") return <Loading label="Loading matching sections…" />;
  if (state.status === "error") return <LoadError onRetry={retry} message="Unable to load these sections. Check your connection and try again." />;
  return <SectionsView key={`${q}:${offset}`} sections={state.data} navigate={navigate} />;
}

/** Past records for every match, including courses and people with nothing this term. */
function PastGrades({ term, data, offered, historyLoader }: { term: string; data: DiscoveryResponse; offered: boolean; historyLoader: HistoryLoader }) {
  const [selection, setSelection] = useState<string | null>(null);
  const termLabel = termSpan(term, term);
  return <details open={!offered} className="rounded border border-line p-4 text-sm">
    <summary className="cursor-pointer font-semibold">Past grade records for these matches</summary>
    <ul className="mt-3 space-y-3">
      {data.courses.map(course => {
        const key = `course:${course.course_id}`;
        return <li key={key} className="min-w-0">
          <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
            <span className="min-w-0 break-words"><strong className="font-semibold">{course.subject} {course.course_number}</strong> {course.title}{course.current_sections ? "" : <span className="text-slate"> · Not offered in {termLabel}</span>}</span>
            <button className="rounded border border-silver px-3 py-2" aria-expanded={selection === key} onClick={() => setSelection(selection === key ? null : key)}>Grade history for {course.subject} {course.course_number}</button>
          </div>
          {selection === key ? <HistoryPanel key={key} term={term} courseId={course.course_id} name={null} historyLoader={historyLoader} /> : null}
        </li>;
      })}
      {data.instructors.map(match => {
        const key = `${match.course_id}:${match.name}`;
        return <li key={key} className="min-w-0">
          <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
            <span className="flex min-w-0 flex-wrap items-center gap-x-1 break-words"><span className="font-semibold">{match.name}</span><RmpLink instructor={match.name} subject={match.subject} /> {match.subject} {match.course_number}{match.current_sections ? "" : <span className="text-slate"> · Not teaching it in {termLabel}</span>}</span>
            <button className="rounded border border-silver px-3 py-2" aria-expanded={selection === key} onClick={() => setSelection(selection === key ? null : key)}>Grade history for {match.name} in {match.subject} {match.course_number}</button>
          </div>
          {selection === key ? <HistoryPanel key={key} term={term} courseId={match.course_id} name={match.name} historyLoader={historyLoader} /> : null}
        </li>;
      })}
    </ul>
    {data.instructors.length ? <p className="mt-3 text-slate">{data.identity_note}</p> : null}
  </details>;
}

export function DiscoveryPage({ term, q, discoveryLoader, historyLoader, rankingLoader, navigate }: {
  term: string; q: string; discoveryLoader: DiscoveryLoader; historyLoader: HistoryLoader; rankingLoader: RankingLoader;
  navigate: (route: Route) => void;
}) {
  const [offset, setOffset] = useState(0);
  const [state, retry] = useLoad(`${term}:${q}:${offset}`, signal => discoveryLoader(term, q, offset, signal));
  if (state.status === "loading") return <Loading label="Searching courses and instructors…" />;
  if (state.status === "error") return <LoadError onRetry={retry} message="Unable to search courses and instructors. Check your connection and try again." />;
  const data = state.data;
  if (!data.course_total && !data.instructor_total) return <Notice title={`Nothing matches "${q}"`}>Try a CRN, course code, number, official title, or professor's listed name. Initials can't be expanded into a full name.</Notice>;
  const offered = sectionFilters(term, data).length > 0;
  return <div className="space-y-6">
    <div>
      <h1 className="mb-1 break-words text-2xl font-semibold">Classes matching “{q}”</h1>
      <p className="text-xs text-slate">From USF's catalog and class schedule, checked {new Date(data.as_of).toLocaleString("en-US", { timeZone: "America/New_York" })}</p>
    </div>
    <section aria-label="Matching classes">
      <MatchedSections term={term} q={q} offset={offset} data={data} rankingLoader={rankingLoader} navigate={navigate} />
    </section>
    {Math.max(data.course_total, data.instructor_total) > 20 ? <Pagination offset={offset} total={Math.max(data.course_total, data.instructor_total)} onPage={setOffset} /> : null}
    <PastGrades key={`${q}:${offset}`} term={term} data={data} offered={offered} historyLoader={historyLoader} />
  </div>;
}
