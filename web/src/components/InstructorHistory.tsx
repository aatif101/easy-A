import { useState } from "react";

import { formatShare, termSpan, type SectionView } from "../lib/section";
import { GradeBar } from "./GradeBar";

const SOURCE_NOTE =
  'Source: USF InfoCenter grade reports, matched to instructors in the USF class schedule. "% A" is the share of A–F grades that were an A.';
const CO_TEACH_NOTE =
  "USF lists one instructor per section; co-taught courses are attributed to the listed instructor.";

const INITIAL = 8;

/** Everyone with recorded grades in this course, so students can compare instructors. */
export function InstructorHistory({ view, courseCode }: { view: SectionView; courseCode: string }) {
  const [showAll, setShowAll] = useState(false);
  if (view.history.length === 0) {
    return (
      <p className="text-sm text-slate">
        {view.kind === "lab"
          ? "Lab sections don't give letter grades, so there is no A rate to show."
          : `No instructor-level grade history is recorded for ${courseCode}.`}
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold">Everyone who has taught {courseCode} recently</h3>
      <ul className="flex max-w-3xl flex-col">
        {(showAll ? view.history : view.history.slice(0, INITIAL)).map((row) => (
          <li
            key={row.name}
            className="grid grid-cols-[minmax(0,1fr)_120px_48px] items-center gap-3 border-b border-line py-1.5 text-sm last:border-b-0 sm:grid-cols-[minmax(0,1fr)_160px_48px_minmax(0,1.4fr)]"
          >
            <span className="min-w-0 truncate" title={row.name}>
              {row.name}
              {row.is_current ? <span className="ml-2 text-xs font-semibold text-green">This section</span> : null}
            </span>
            <GradeBar share={row.a_share} faded={!row.scored} />
            <span className="tabular text-right font-semibold">{formatShare(row.a_share)}</span>
            <span className="tabular col-span-3 text-xs text-slate sm:col-span-1 sm:whitespace-nowrap">
              {row.effective_n.toLocaleString("en-US")} grades · {termSpan(row.first_term, row.last_term)}
              {row.scored ? "" : " · too few"}
            </span>
          </li>
        ))}
      </ul>
      {view.history.length > INITIAL ? (
        <button
          type="button"
          onClick={() => setShowAll(!showAll)}
          aria-expanded={showAll}
          className="h-9 self-start rounded-md border border-silver bg-white px-3 text-sm font-semibold hover:bg-wash"
        >
          {showAll ? "Show fewer" : `Show all ${view.history.length} instructors`}
        </button>
      ) : null}
      {view.otherInstructorCount > 0 ? (
        <p className="text-xs text-slate">
          Plus {view.otherInstructorCount} more {view.otherInstructorCount === 1 ? "instructor" : "instructors"} with only a few grades.
        </p>
      ) : null}
      <p className="max-w-2xl text-xs text-slate">
        {SOURCE_NOTE} {CO_TEACH_NOTE}
      </p>
    </div>
  );
}
