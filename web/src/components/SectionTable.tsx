import { Fragment, useState } from "react";

import { formatShare, seatsText, type SectionView } from "../lib/section";
import type { SectionRanking } from "../types/rankings";
import { CopyCrnButton } from "./CopyCrnButton";
import { GradeBar, GradeLegend } from "./GradeBar";
import { InstructorHistory } from "./InstructorHistory";
import { RmpSearchLink } from "./RmpSearchLink";

export interface SectionRow {
  ranking: SectionRanking;
  view: SectionView;
}

interface SectionTableProps {
  rows: SectionRow[];
  showCourse?: boolean;
  onOpenCourse?: (subject: string, courseNumber: string) => void;
}

const courseCode = (ranking: SectionRanking) => `${ranking.subject} ${ranking.course_number}`;

const aShareClass = (view: SectionView) =>
  view.kind === "instructor" ? "text-ink" : "text-slate";

const captionClass = (view: SectionView) =>
  view.kind === "no_history" || view.kind === "unnamed" || view.kind === "thin" ? "text-warn" : "text-slate";

function Evidence({ view }: { view: SectionView }) {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      {view.aShare !== null ? <GradeBar share={view.aShare} faded={view.kind === "thin"} /> : null}
      <span className={`tabular text-xs ${captionClass(view)}`}>{view.caption}</span>
    </div>
  );
}

function Seats({ view }: { view: SectionView }) {
  return (
    <span className="tabular">
      {seatsText(view)}
      {view.seatsStale ? <span className="block text-xs text-warn">may be out of date</span> : null}
    </span>
  );
}

function CourseLink({ ranking, onOpenCourse }: { ranking: SectionRanking; onOpenCourse?: SectionTableProps["onOpenCourse"] }) {
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

export function SectionTable({ rows, showCourse = false, onOpenCourse }: SectionTableProps) {
  const [open, setOpen] = useState<string | null>(null);
  const toggle = (crn: string) => setOpen((current) => (current === crn ? null : crn));
  const columnCount = showCourse ? 7 : 6;

  return (
    <>
      <div className="hidden overflow-x-auto rounded-lg border border-line min-[900px]:block">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-wash text-left text-slate">
              <th scope="col" className="px-3.5 py-2.5 font-medium">CRN</th>
              {showCourse ? <th scope="col" className="px-3.5 py-2.5 font-medium">Course</th> : null}
              <th scope="col" className="px-3.5 py-2.5 font-medium">Instructor</th>
              <th scope="col" className="w-[240px] px-3.5 py-2.5 font-medium">
                <span className="flex items-center gap-2.5 whitespace-nowrap">
                  Instructor's grades in this course <GradeLegend />
                </span>
              </th>
              <th scope="col" className="px-3.5 py-2.5 text-right font-medium">A%</th>
              <th scope="col" className="px-3.5 py-2.5 text-right font-medium">Seats</th>
              <th scope="col" className="w-12 px-2 py-2.5">
                <span className="sr-only">Instructor comparison</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ ranking, view }) => {
              const isOpen = open === ranking.crn;
              return (
                <Fragment key={ranking.crn}>
                  <tr className={`border-t border-line align-middle ${isOpen ? "bg-[#FAFAF6]" : ""}`}>
                    <td className="px-3.5 py-3">
                      <span className="flex items-center gap-2">
                        <span className="font-mono font-medium">{ranking.crn}</span>
                        <CopyCrnButton crn={ranking.crn} />
                      </span>
                    </td>
                    {showCourse ? (
                      <td className="px-3.5 py-3">
                        <CourseLink ranking={ranking} onOpenCourse={onOpenCourse} />
                        <span className="block max-w-[220px] truncate text-xs text-slate" title={ranking.course_title}>
                          {ranking.course_title}
                        </span>
                      </td>
                    ) : null}
                    <td className="px-3.5 py-3">
                      <div className="flex flex-wrap items-center gap-x-1">
                        <span className={view.instructorNamed ? "" : "text-slate"}>{view.instructor}</span>
                        {view.instructorNamed && ranking.instructor_provenance.freshness !== "unavailable" ? (
                          <RmpSearchLink instructor={view.instructor} />
                        ) : null}
                      </div>
                      {view.delivery ? <span className="block text-xs text-slate">{view.delivery}</span> : null}
                    </td>
                    <td className="px-3.5 py-3">
                      <Evidence view={view} />
                    </td>
                    <td className="px-3.5 py-3 text-right">
                      <span className={`tabular text-lg font-bold ${aShareClass(view)}`}>
                        {view.aShare === null ? "—" : formatShare(view.aShare)}
                      </span>
                    </td>
                    <td className="px-3.5 py-3 text-right">
                      <Seats view={view} />
                    </td>
                    <td className="px-2 py-1.5">
                      {view.history.length > 0 || view.kind === "lab" ? (
                        <button
                          type="button"
                          onClick={() => toggle(ranking.crn)}
                          aria-expanded={isOpen}
                          aria-label={`Compare instructors for CRN ${ranking.crn}`}
                          className="flex h-10 w-10 items-center justify-center rounded-md hover:bg-wash"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#303434" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ transform: isOpen ? "rotate(180deg)" : undefined }}>
                            <path d="M6 9l6 6 6-6" />
                          </svg>
                        </button>
                      ) : null}
                    </td>
                  </tr>
                  {isOpen ? (
                    <tr className="bg-[#FAFAF6]">
                      <td colSpan={columnCount} className="px-3.5 pb-5 pt-1">
                        <InstructorHistory view={view} courseCode={courseCode(ranking)} />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      <ul className="flex flex-col gap-2.5 min-[900px]:hidden">
        {rows.map(({ ranking, view }) => {
          const isOpen = open === ranking.crn;
          return (
            <li key={ranking.crn} className="flex flex-col gap-2.5 rounded-lg border border-line px-4 py-3.5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  {showCourse ? (
                    <div className="text-sm">
                      <CourseLink ranking={ranking} onOpenCourse={onOpenCourse} />
                    </div>
                  ) : null}
                  <div className="flex flex-wrap items-center gap-x-1">
                    <span className={`min-w-0 break-words font-semibold ${view.instructorNamed ? "" : "text-slate"}`}>{view.instructor}</span>
                    {view.instructorNamed && ranking.instructor_provenance.freshness !== "unavailable" ? (
                      <RmpSearchLink instructor={view.instructor} />
                    ) : null}
                  </div>
                  <div className="text-[13px] text-slate">
                    <span className="font-mono text-ink">{ranking.crn}</span>
                    {view.delivery ? ` · ${view.delivery}` : ""} · {seatsText(view)} seats
                    {view.seatsStale ? " (may be out of date)" : ""}
                  </div>
                </div>
                <span className={`tabular text-2xl font-bold leading-tight ${aShareClass(view)}`}>
                  {view.aShare === null ? "—" : formatShare(view.aShare)}
                </span>
              </div>
              <Evidence view={view} />
              <div className="flex flex-wrap gap-2">
                <CopyCrnButton crn={ranking.crn} large />
                {view.history.length > 0 ? (
                  <button
                    type="button"
                    onClick={() => toggle(ranking.crn)}
                    aria-expanded={isOpen}
                    className="h-10 rounded-md border border-silver bg-white px-3.5 text-sm font-semibold hover:bg-wash"
                  >
                    {isOpen ? "Hide instructors" : "Compare instructors"}
                  </button>
                ) : null}
              </div>
              {isOpen ? <InstructorHistory view={view} courseCode={courseCode(ranking)} /> : null}
            </li>
          );
        })}
      </ul>
    </>
  );
}
