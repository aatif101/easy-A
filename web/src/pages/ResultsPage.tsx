import { Chip, SectionsView } from "../components/SectionsView";
import { SectionTable } from "../components/SectionTable";
import { LoadError, Loading, Notice } from "../components/Status";
import { loadAllSections } from "../lib/loadAll";
import { inAppClick, type InstructorSelection, type Route } from "../lib/route";
import { GEN_ED_AREAS, REQUIREMENT_CODES, findGenEdArea, parseSearch } from "../lib/search";
import { toRows } from "../lib/section";
import { useLoad } from "../lib/useLoad";
import type { RankingLoader, SectionLoader } from "../types/rankings";
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

function CourseResults({ subject, courseNumber, instructor, term, rankingLoader, navigate, discoveryLoader, historyLoader }: Loaders & { subject: string; courseNumber: string; instructor?: InstructorSelection }) {
  const [state, retry] = useLoad(`${term}:${subject}:${courseNumber}:${instructor?.courseId ?? ""}:${instructor?.name ?? ""}`, (signal) =>
    loadAllSections(rankingLoader, [{ term, subject, course_number: courseNumber, ...(instructor ? { course_id: instructor.courseId, instructor: instructor.name } : {}) }], signal),
  );
  const code = `${subject} ${courseNumber}`;
  if (state.status === "loading") return <Loading label={`Loading ${code} sections…`} />;
  if (state.status === "error") return <LoadError onRetry={retry} />;
  const allSections: Route = { view: "search", q: code };
  const instructorNotice = instructor ? <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
    <p className="break-words">Showing sections assigned to <strong>{instructor.name}</strong> in {code}.</p>
    <a href={`?q=${encodeURIComponent(code)}`} onClick={inAppClick(navigate, allSections)}>Show all {code} sections</a>
  </div> : null;
  if (state.data.length === 0) {
    if (instructor) return <>{instructorNotice}<Notice title={`No current ${code} sections for ${instructor.name}`}>The stored schedule may have changed. Show all course sections to see who else is teaching it.</Notice></>;
    return (
      <><Notice title={`No Spring 2027 sections of ${code}`}>
        Check the course code, or{" "}
        <a href={`?q=${subject}`} onClick={inAppClick(navigate, { view: "search", q: subject })}>
          see every {subject} section
        </a>
        .
      </Notice><div className="mt-6"><DiscoveryPage term={term} q={code} discoveryLoader={discoveryLoader} historyLoader={historyLoader} rankingLoader={rankingLoader} navigate={navigate} /></div></>
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
      {instructorNotice}
      <SectionsView sections={state.data} navigate={navigate} />
    </>
  );
}

function SubjectResults(props: Loaders & { subject: string; q: string }) {
  const { subject, term, rankingLoader, navigate } = props;
  const [state, retry] = useLoad(`${term}:${subject}`, (signal) =>
    loadAllSections(rankingLoader, [{ term, subject, sort: "course" }], signal),
  );
  if (state.status === "loading") return <Loading label={`Loading ${subject} sections…`} />;
  if (state.status === "error") return <LoadError onRetry={retry} />;
  // Three letters with no sections may be a name or title ("Lee"); the backend decides.
  if (state.data.length === 0) return <DiscoveryPage {...props} />;
  return (
    <>
      <h1 className="mb-5 text-2xl font-semibold">{subject} sections</h1>
      <SectionsView sections={state.data} navigate={navigate} />
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
      {state.status === "ready" ? <SectionsView key={area.id} sections={state.data} navigate={navigate} /> : null}
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
        onOpenCourse={(subject, courseNumber) => navigate({ view: "search", q: `${subject} ${courseNumber}` })}
      />
      <a href={`?q=${encodeURIComponent(code)}`} onClick={inAppClick(navigate, { view: "search", q: code })} className="mt-3 inline-block text-sm font-semibold">
        See every {code} section
      </a>
    </>
  );
}

/**
 * CRNs, course codes and subjects load sections directly, as before, so the common searches never
 * wait on (or break with) discovery. Numbers, titles and professor names go to discovery.
 */
export function SearchResults(props: Loaders & { q: string; instructor?: InstructorSelection }) {
  const parsed = parseSearch(props.q);
  if (parsed.kind === "crn") return <CrnResult {...props} crn={parsed.crn} />;
  if (parsed.kind === "course") {
    return <CourseResults {...props} subject={parsed.subject} courseNumber={parsed.courseNumber} />;
  }
  if (parsed.kind === "subject") return <SubjectResults {...props} subject={parsed.subject} />;
  return <DiscoveryPage {...props} />;
}
