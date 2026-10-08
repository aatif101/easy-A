import type { ReactNode } from "react";

import { aShareClass, courseCode, formatShare, seatsText, type SectionView } from "../lib/section";
import type { SectionRanking } from "../types/rankings";
import { CopyCrnButton } from "./CopyCrnButton";
import { GradeBar } from "./GradeBar";
import { InstructorHistory } from "./InstructorHistory";
import { RmpLink } from "./RmpLink";

const captionClass = (view: SectionView) =>
  view.kind === "no_history" || view.kind === "unnamed" || view.kind === "thin" ? "text-warn" : "text-slate";

export function Evidence({ view }: { view: SectionView }) {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      {view.aShare !== null ? <GradeBar share={view.aShare} faded={view.kind === "thin"} /> : null}
      <span className={`tabular text-xs ${captionClass(view)}`}>{view.caption}</span>
    </div>
  );
}

export function CourseLink({ ranking, onOpenCourse }: { ranking: SectionRanking; onOpenCourse?: (subject: string, courseNumber: string) => void }) {
  const code = courseCode(ranking);
  return (
    <a
      href={`?q=${encodeURIComponent(code)}`}
      onClick={(event) => {
        if (!onOpenCourse || event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
        event.preventDefault();
        onOpenCourse(ranking.subject, ranking.course_number);
      }}
      className="font-semibold text-ink no-underline hover:underline"
    >
      {code}
    </a>
  );
}

/** A numbered dot that points at one part of a card; the reading key repeats the number. */
export function Marker({ n }: { n: number }) {
  return (
    <span aria-hidden="true" className="flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-full bg-ink text-xs font-bold text-white">
      {n}
    </span>
  );
}

interface SectionCardProps {
  ranking: SectionRanking;
  view: SectionView;
  showCourse?: boolean;
  onOpenCourse?: (subject: string, courseNumber: string) => void;
  open: boolean;
  onToggle: () => void;
  /** Numbered dots beside the A%, grade bar, RMP link and Copy CRN, for the reading key. */
  markers?: boolean;
  children?: ReactNode;
}

/** One section as a card: the phone layout of results, and the home page preview. */
export function SectionCard({ ranking, view, showCourse = false, onOpenCourse, open, onToggle, markers = false, children }: SectionCardProps) {
  const mark = (n: number) => (markers ? <Marker n={n} /> : null);
  return (
    <li className="flex flex-col gap-2.5 rounded-lg border border-line px-4 py-3.5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {showCourse ? (
            <div className="text-sm">
              <CourseLink ranking={ranking} onOpenCourse={onOpenCourse} />
            </div>
          ) : null}
          <div className="flex flex-wrap items-center gap-x-1">
            <span className={`min-w-0 break-words font-semibold ${view.instructorNamed ? "" : "text-slate"}`}>{view.instructor}</span>
            {view.rmpLinkable ? <RmpLink instructor={view.instructor} subject={view.subject} /> : null}
            {mark(3)}
          </div>
          <div className="text-[13px] text-slate">
            <span className="font-mono text-ink">{ranking.crn}</span>
            {view.delivery ? ` · ${view.delivery}` : ""} · {seatsText(view)} seats
            {view.seatsStale ? " (may be out of date)" : ""}
          </div>
        </div>
        <span className="flex shrink-0 items-center gap-2">
          {mark(1)}
          <span className={`tabular text-2xl font-bold leading-tight ${aShareClass(view)}`}>
            {view.aShare === null ? "—" : formatShare(view.aShare)}
          </span>
        </span>
      </div>
      <div className="flex items-center gap-2">
        <div className="min-w-0 flex-1">
          <Evidence view={view} />
        </div>
        {mark(2)}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <CopyCrnButton crn={ranking.crn} large />
        {mark(4)}
        {view.history.length > 0 ? (
          <button
            type="button"
            onClick={onToggle}
            aria-expanded={open}
            className="h-10 rounded-md border border-silver bg-white px-3.5 text-sm font-semibold hover:bg-wash"
          >
            {open ? "Hide instructors" : "Compare instructors"}
          </button>
        ) : null}
      </div>
      {open ? <InstructorHistory view={view} courseCode={courseCode(ranking)} /> : null}
      {children}
    </li>
  );
}
