import { useState } from "react";

import { RmpLink } from "../components/RmpLink";
import { LoadError, Loading, Notice } from "../components/Status";
import { inAppClick, type Route } from "../lib/route";
import { formatShare, termSpan } from "../lib/section";
import { useLoad } from "../lib/useLoad";
import type { DiscoveryLoader, HistoryLoader } from "../types/search";

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
      <details className="text-xs text-slate"><summary>Source fingerprint</summary><p className="break-all">{row.source_hash}</p></details>
    </li>)}</ul>
    {data.total > 20 ? <Pagination offset={offset} total={data.total} onPage={setOffset} /> : null}
  </div>;
}

export function DiscoveryPage({ term, q, discoveryLoader, historyLoader, navigate }: {
  term: string; q: string; discoveryLoader: DiscoveryLoader; historyLoader: HistoryLoader;
  navigate: (route: Route) => void;
}) {
  const [offset, setOffset] = useState(0);
  const [selection, setSelection] = useState<string | null>(null);
  const [state, retry] = useLoad(`${term}:${q}:${offset}`, signal => discoveryLoader(term, q, offset, signal));
  if (state.status === "loading") return <Loading label="Searching courses and instructors…" />;
  if (state.status === "error") return <LoadError onRetry={retry} message="Unable to search courses and instructors. Check your connection and try again." />;
  const data = state.data;
  if (!data.course_total && !data.instructor_total) return <Notice title={`Nothing matches "${q}"`}>Try a CRN, course code, number, official title, or stored professor name. Initials cannot be expanded into a full name.</Notice>;
  return <div className="space-y-6">
    <p className="text-xs text-slate">Source: stored USF catalog and class schedule · Database read {new Date(data.as_of).toLocaleString("en-US", { timeZone: "America/New_York" })}</p>
    <h1 className="break-words text-2xl font-semibold">Matches for “{q}”</h1><section aria-label="Course results">
      <h2 className="mb-3 text-lg font-semibold">Courses ({data.course_total})</h2>
      {!data.course_total ? <p className="text-sm text-slate">No matching catalog courses.</p> : null}
      <ul className="space-y-3">{data.courses.map(course => {
        const key = `course:${course.course_id}`;
        const route: Route = { view: "search", q: `${course.subject} ${course.course_number}` };
        return <li key={key} className="min-w-0 rounded border border-line p-4">
          <h3 className="break-words font-semibold">{course.subject} {course.course_number} · {course.title}</h3>
          <p className="mt-1 text-sm text-slate">Catalog {course.catalog_edition} · {course.current_sections} current sections in {termSpan(term, term)}</p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            {course.current_sections ? <a href={`?q=${encodeURIComponent(route.q)}`} onClick={inAppClick(navigate, route)}>Compare current sections</a> : <span className="text-sm text-slate">No current sections; historical records are separate.</span>}
            <button className="rounded border border-silver px-3 py-2 text-sm" aria-expanded={selection === key} onClick={() => setSelection(selection === key ? null : key)}>Grade history for {course.subject} {course.course_number}</button>
          </div>
          {selection === key ? <HistoryPanel key={key} term={term} courseId={course.course_id} name={null} historyLoader={historyLoader} /> : null}
        </li>;
      })}</ul>
    </section>
    <section aria-label="Instructor results">
      <h2 className="mb-3 text-lg font-semibold">Instructors by course ({data.instructor_total})</h2>
      <p className="mb-3 text-sm text-slate">{data.identity_note}</p>
      {!data.instructor_total ? <p className="text-sm text-slate">No matching named instructors.</p> : null}
      <ul className="space-y-3">{data.instructors.map(instructor => {
        const key = `${instructor.course_id}:${instructor.name}`;
        return <li key={key} className="min-w-0 rounded border border-line p-4">
          <h3 className="break-words font-semibold">{instructor.subject} {instructor.course_number} · {instructor.title}</h3>
          <p className="mt-1 flex flex-wrap items-center gap-x-1 break-words">Listed instructor: <span>{instructor.name}</span><RmpLink instructor={instructor.name} subject={instructor.subject} /></p>
          <p className="mt-1 text-sm text-slate">{instructor.current_sections} current assignments · {instructor.historical_sections} historical assignments · Schedule observed {new Date(instructor.observed_at).toLocaleDateString("en-US", { timeZone: "America/New_York" })}</p>
          {instructor.current_sections ? <a className="mt-2 block" href={`?q=${encodeURIComponent(`${instructor.subject} ${instructor.course_number}`)}`} onClick={inAppClick(navigate, { view: "search", q: `${instructor.subject} ${instructor.course_number}` })}>Compare current {instructor.subject} {instructor.course_number} sections</a> : null}
          <button className="mt-2 rounded border border-silver px-3 py-2 text-sm" aria-expanded={selection === key} onClick={() => setSelection(selection === key ? null : key)}>Grade history for {instructor.name} in {instructor.subject} {instructor.course_number}</button>
          {selection === key ? <HistoryPanel key={key} term={term} courseId={instructor.course_id} name={instructor.name} historyLoader={historyLoader} /> : null}
        </li>;
      })}</ul>
    </section>
    {Math.max(data.course_total, data.instructor_total) > 20 ? <Pagination offset={offset} total={Math.max(data.course_total, data.instructor_total)} onPage={page => { setSelection(null); setOffset(page); }} /> : null}
  </div>;
}
