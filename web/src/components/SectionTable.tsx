import { Fragment, useState } from "react";

import { aShareClass, courseCode, formatShare, seatsText, type SectionView } from "../lib/section";
import type { SectionRanking } from "../types/rankings";
import { CopyCrnButton } from "./CopyCrnButton";
import { GradeLegend } from "./GradeBar";
import { InstructorHistory } from "./InstructorHistory";
import { RmpLink } from "./RmpLink";
import { CourseLink, Evidence, SectionCard } from "./SectionCard";

export interface SectionRow {
  ranking: SectionRanking;
  view: SectionView;
}

interface SectionTableProps {
  rows: SectionRow[];
  showCourse?: boolean;
  onOpenCourse?: (subject: string, courseNumber: string) => void;
}

function Seats({ view }: { view: SectionView }) {
  return (
    <span className="tabular">
      {seatsText(view)}
      {view.seatsStale ? <span className="block text-xs text-warn">may be out of date</span> : null}
    </span>
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
                        {view.rmpLinkable ? (
                          <RmpLink instructor={view.instructor} subject={view.subject} />
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
        {rows.map(({ ranking, view }) => (
          <SectionCard
            key={ranking.crn}
            ranking={ranking}
            view={view}
            showCourse={showCourse}
            onOpenCourse={onOpenCourse}
            open={open === ranking.crn}
            onToggle={() => toggle(ranking.crn)}
          />
        ))}
      </ul>
    </>
  );
}
