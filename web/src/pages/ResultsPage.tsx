import { useMemo, useState, type ReactNode } from "react";

import { SectionTable, type SectionRow } from "../components/SectionTable";
import { LoadError, Loading, Notice } from "../components/Status";
import { loadAllSections } from "../lib/loadAll";
import { inAppClick, type Route } from "../lib/route";
import { GEN_ED_AREAS, REQUIREMENT_CODES, findGenEdArea } from "../lib/search";
import { sortSections, toSectionView, type SectionSort } from "../lib/section";
import { useLoad } from "../lib/useLoad";
import type { RankingLoader, SectionLoader, SectionRanking } from "../types/rankings";
import type { DiscoveryLoader, HistoryLoader } from "../types/search";
import { DiscoveryPage } from "./DiscoveryPage";

interface Loaders {
  term: string;
  rankingLoader: RankingLoader;
  sectionLoader: SectionLoader;
  navigate: (route: Route) => void;
  discoveryLoader: DiscoveryLoader;
  historyLoader: HistoryLoader;
}

const toRows = (items: SectionRanking[]): SectionRow[] =>
  items.map((ranking) => ({ ranking, view: toSectionView(ranking) }));

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={`h-9 rounded-full border px-3 text-sm ${
        on ? "border-ink bg-ink text-white" : "border-silver bg-white text-ink hover:bg-wash"
      }`}
    >
      {children}
    </button>
  );
}

type Mode = "" | "in_person" | "online";

/** A fully loaded set of sections with client-side filters and sorting. */
function SectionsView({
  sections,
  showCourse,
  navigate,
}: {
  sections: SectionRanking[];
  showCourse: boolean;
  navigate: Loaders["navigate"];
}) {
  const [sort, setSort] = useState<SectionSort>("a_share");
  const [hasHistory, setHasHistory] = useState(false);
  const [openSeats, setOpenSeats] = useState(false);
  const [mode, setMode] = useState<Mode>("");

  const all = useMemo(() => toRows(sections), [sections]);
  const rows = sortSections(
    all.filter(
      ({ view }) =>
        (!hasHistory || view.kind === "instructor" || view.kind === "thin") &&
        (!openSeats || (view.seatsOpen ?? 0) > 0) &&
        (mode === "" ||
          (mode === "in_person"
            ? view.delivery === "In person"
            : view.delivery === "Online" || view.delivery === "Mostly online")),
    ),
    sort,
  );

  return (
    <>
      <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter sections">
          <Chip on={hasHistory} onClick={() => setHasHistory(!hasHistory)}>Has grade history</Chip>
          <Chip on={openSeats} onClick={() => setOpenSeats(!openSeats)}>Open seats</Chip>
          <Chip on={mode === "in_person"} onClick={() => setMode(mode === "in_person" ? "" : "in_person")}>In person</Chip>
          <Chip on={mode === "online"} onClick={() => setMode(mode === "online" ? "" : "online")}>Online</Chip>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate">
          Sort
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as SectionSort)}
            className="h-9 rounded-md border border-silver bg-white px-2 text-sm text-ink"
          >
            <option value="a_share">Most A's</option>
            <option value="seats">Most seats open</option>
            <option value="crn">CRN</option>
          </select>
        </label>
      </div>
      {rows.length === 0 ? (
        <Notice title="No sections match these filters">Turn a filter off to see more sections.</Notice>
      ) : (
        <SectionTable
          rows={rows}
          showCourse={showCourse}
          onOpenCourse={(subject, courseNumber) => navigate({ view: "search", q: `${subject} ${courseNumber}` })}
        />
      )}
      <p className="mt-3 text-sm text-slate" role="status">
        Showing {rows.length} of {all.length} {all.length === 1 ? "section" : "sections"}
      </p>
    </>
  );
}

function CourseResults({ subject, courseNumber, term, rankingLoader, navigate, discoveryLoader, historyLoader }: Loaders & { subject: string; courseNumber: string }) {
  const [state, retry] = useLoad(`${term}:${subject}:${courseNumber}`, (signal) =>
    loadAllSections(rankingLoader, [{ term, subject, course_number: courseNumber }], signal),
  );
  const code = `${subject} ${courseNumber}`;
  if (state.status === "loading") return <Loading label={`Loading ${code} sections…`} />;
  if (state.status === "error") return <LoadError onRetry={retry} />;
  if (state.data.length === 0) {
    return (
      <><Notice title={`No Spring 2027 sections of ${code}`}>
        Check the course code, or{" "}
        <a href={`?q=${subject}`} onClick={inAppClick(navigate, { view: "search", q: subject })}>
          see every {subject} section
        </a>
        .
      </Notice><div className="mt-6"><DiscoveryPage term={term} q={code} discoveryLoader={discoveryLoader} historyLoader={historyLoader} navigate={navigate} /></div></>
    );
  }
  const first = state.data[0];
  const requirements = first.gened_attributes.filter(({ code: attr }) => REQUIREMENT_CODES.has(attr));
  return (
    <>
      <div className="mb-5">
        <h1 className="text-2xl font-semibold leading-tight">
          {code} <span className="font-normal text-slate">{first.course_title}</span>
        </h1>
        {requirements.length ? (
          <p className="mt-1 text-sm text-slate">{requirements.map(({ label }) => label).join(" · ")}</p>
        ) : null}
      </div>
      <SectionsView sections={state.data} showCourse={false} navigate={navigate} />
    </>
  );
}

function SubjectResults({ subject, term, rankingLoader, navigate }: Loaders & { subject: string }) {
  const [state, retry] = useLoad(`${term}:${subject}`, (signal) =>
    loadAllSections(rankingLoader, [{ term, subject, sort: "course" }], signal),
  );
  if (state.status === "loading") return <Loading label={`Loading ${subject} sections…`} />;
  if (state.status === "error") return <LoadError onRetry={retry} />;
  if (state.data.length === 0) {
    return (
      <Notice title={`No Spring 2027 sections in ${subject}`}>
        Subjects are three letters, like <span className="font-mono">PSY</span> or <span className="font-mono">ENC</span>.
      </Notice>
    );
  }
  return (
    <>
      <h1 className="mb-5 text-2xl font-semibold">{subject} sections</h1>
      <SectionsView sections={state.data} showCourse navigate={navigate} />
    </>
  );
}

export function GenEdResults({ area: areaId, term, rankingLoader, navigate }: Loaders & { area: string }) {
  const area = findGenEdArea(areaId);
  const [state, retry] = useLoad(area ? `${term}:${area.id}` : null, (signal) =>
    loadAllSections(rankingLoader, (area?.codes ?? []).map((code) => ({ term, gened_code: code })), signal),
  );
  const chips = (
    <div role="group" aria-label="Gen Ed requirement" className="mt-3 flex flex-wrap gap-1.5">
      {GEN_ED_AREAS.map((item) => (
        <Chip key={item.id} on={item.id === area?.id} onClick={() => navigate({ view: "gened", area: item.id })}>
          {item.label}
        </Chip>
      ))}
    </div>
  );
  if (!area) {
    return (
      <>
        <Notice title="Unknown Gen Ed requirement">Pick one of the requirements below.</Notice>
        {chips}
      </>
    );
  }
  return (
    <>
      <div className="mb-5">
        <h1 className="text-2xl font-semibold">{area.label}</h1>
        <p className="mt-1 text-sm text-slate">Sections that count toward the Gen Ed {area.label} requirement</p>
        {chips}
      </div>
      {state.status === "loading" ? <Loading label={`Loading ${area.label} sections…`} /> : null}
      {state.status === "error" ? <LoadError onRetry={retry} /> : null}
      {state.status === "ready" ? <SectionsView key={area.id} sections={state.data} showCourse navigate={navigate} /> : null}
    </>
  );
}

function CrnResult({ crn, term, sectionLoader, navigate }: Loaders & { crn: string }) {
  const [state, retry] = useLoad(`${term}:${crn}`, (signal) => sectionLoader(term, crn, signal));
  if (state.status === "loading") return <Loading label={`Looking up CRN ${crn}…`} />;
  if (state.status === "error") return <LoadError onRetry={retry} />;
  if (state.data === null) {
    return (
      <Notice title={`No Spring 2027 section with CRN ${crn}`}>
        Check the number in OASIS, or search the course code instead.
      </Notice>
    );
  }
  const ranking = state.data;
  const code = `${ranking.subject} ${ranking.course_number}`;
  return (
    <>
      <h1 className="mb-4 text-2xl font-semibold">CRN {crn}</h1>
      <SectionTable
        rows={toRows([ranking])}
        showCourse
        onOpenCourse={(subject, courseNumber) => navigate({ view: "search", q: `${subject} ${courseNumber}` })}
      />
      <a href={`?q=${encodeURIComponent(code)}`} onClick={inAppClick(navigate, { view: "search", q: code })} className="mt-3 inline-block text-sm font-semibold">
        Compare every {code} section
      </a>
    </>
  );
}

export function SearchResults(props: Loaders & { q: string }) {
  const [state, retry] = useLoad(`${props.term}:${props.q}`, signal => props.discoveryLoader(props.term, props.q, 0, signal));
  if (state.status === "loading") return <Loading label="Searching courses and instructors…" />;
  if (state.status === "error") return <LoadError onRetry={retry} />;
  const data = state.data;
  if (data.kind === "subject" && !data.course_total && data.instructor_total) return <DiscoveryPage {...props} initialData={data} />;
  if (data.kind === "crn" && data.crn) return <CrnResult {...props} crn={data.crn} />;
  if (data.kind === "course") {
    return <CourseResults {...props} subject={data.subject} courseNumber={data.course_number} />;
  }
  if (data.kind === "subject") return <><SubjectResults {...props} subject={data.subject} /><div className="mt-6"><DiscoveryPage {...props} initialData={data} instructorsOnly /></div></>;
  return <DiscoveryPage {...props} initialData={data} />;
}
