import { Fragment, useState, type ReactNode } from "react";

import { seatsText, waitlistText, type SectionRow, type SectionSort, type SectionView } from "../lib/section";
import type { SectionRanking } from "../types/rankings";
import { CopyCrnButton } from "./CopyCrnButton";
import { GradeBar, GradeLegend, GradeNumbers } from "./GradeBar";
import { InstructorHistory } from "./InstructorHistory";
import { RmpLink } from "./RmpLink";

interface SectionTableProps {
  rows: SectionRow[];
  /** Leave both unset for a fixed list: the headers then stay plain text. */
  sort?: SectionSort;
  onSort?: (sort: SectionSort) => void;
  onOpenCourse?: (subject: string, courseNumber: string) => void;
}

const courseCode = (ranking: SectionRanking) => `${ranking.subject} ${ranking.course_number}`;

function Evidence({ view }: { view: SectionView }) {
  if (view.aShare === null) return <span className="text-[13px] text-slate">{view.caption}</span>;
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <GradeBar share={view.aShare} grades={view.grades} faded={view.kind === "thin"} />
      <GradeNumbers share={view.aShare} grades={view.grades} />
      <span className={`tabular text-xs ${view.kind === "thin" ? "text-warn" : "text-slate"}`}>{view.caption}</span>
    </div>
  );
}

function Seats({ view, showOpen = false }: { view: SectionView; showOpen?: boolean }) {
  const waitlist = waitlistText(view);
  return (
    <span className="tabular">
      <span className="whitespace-nowrap">{seatsText(view)}{showOpen && (view.seatsOpen ?? 0) > 0 ? " open" : ""}</span>
      {waitlist ? <span className="block whitespace-nowrap text-xs text-slate">{waitlist}</span> : null}
      {view.seatsStale ? <span className="block whitespace-nowrap text-xs text-warn">may be out of date</span> : null}
    </span>
  );
}

function Schedule({ view }: { view: SectionView }) {
  return (
    <span className="tabular block">
      {view.schedule.map((line) => (
        <span key={line} className="block whitespace-nowrap">{line}</span>
      ))}
      {view.delivery ? <span className="block text-xs text-slate">{view.delivery}</span> : null}
    </span>
  );
}

function Instructor({ view }: { view: SectionView }) {
  return (
    <div className="flex flex-wrap items-center gap-x-1">
      <span className={`min-w-0 break-words ${view.instructorNamed ? "" : "text-slate"}`}>{view.instructor}</span>
      {view.rmpLinkable ? <RmpLink instructor={view.instructor} subject={view.subject} /> : null}
    </div>
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

function SectionDetails({ row }: { row: SectionRow }) {
  const { ranking, view } = row;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-0.5 text-sm">
        {view.sectionLine ? <p>{view.sectionLine}</p> : null}
        {view.meetingDetails.map((line) => (
          <p key={line} className="tabular text-slate">{line}</p>
        ))}
      </div>
      <InstructorHistory view={view} courseCode={courseCode(ranking)} />
    </div>
  );
}

function SortHeader({ column, sort, onSort, className = "", children }: {
  column: SectionSort;
  sort?: SectionSort;
  onSort?: (sort: SectionSort) => void;
  className?: string;
  children: ReactNode;
}) {
  const active = sort === column;
  return (
    <th scope="col" aria-sort={active ? (column === "a_share" || column === "seats" ? "descending" : "ascending") : undefined} className={`px-3.5 py-2.5 font-medium ${className}`}>
      {onSort ? (
        <button type="button" onClick={() => onSort(column)} className="inline-flex items-center gap-1 whitespace-nowrap font-medium hover:text-ink">
          {children}
          {active ? <span aria-hidden="true">▾</span> : null}
        </button>
      ) : (
        <span className="whitespace-nowrap">{children}</span>
      )}
    </th>
  );
}

/** One row is one class a student can register for, in the same columns on every page. */
export function SectionTable({ rows, sort, onSort, onOpenCourse }: SectionTableProps) {
  const [open, setOpen] = useState<string | null>(null);
  const toggle = (crn: string) => setOpen((current) => (current === crn ? null : crn));

  return (
    <>
      <div className="hidden overflow-x-auto rounded-lg border border-line min-[1100px]:block">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-wash text-left text-slate">
              <SortHeader column="crn" sort={sort} onSort={onSort}>CRN</SortHeader>
              <SortHeader column="course" sort={sort} onSort={onSort}>Course</SortHeader>
              <th scope="col" className="px-3.5 py-2.5 font-medium">Instructor</th>
              <th scope="col" aria-sort={sort === "a_share" ? "descending" : undefined} className="w-[300px] px-3.5 py-2.5 font-medium">
                <span className="flex items-center gap-2.5 whitespace-nowrap">
                  {onSort ? (
                    <button type="button" onClick={() => onSort("a_share")} className="inline-flex items-center gap-1 font-medium hover:text-ink">
                      Instructor's grades in this course
                      {sort === "a_share" ? <span aria-hidden="true">▾</span> : null}
                    </button>
                  ) : (
                    "Instructor's grades in this course"
                  )}
                </span>
                <span className="mt-1 block"><GradeLegend /></span>
              </th>
              <SortHeader column="seats" sort={sort} onSort={onSort}>Seats open</SortHeader>
              <SortHeader column="schedule" sort={sort} onSort={onSort}>Schedule</SortHeader>
              <th scope="col" className="w-12 px-2 py-2.5">
                <span className="sr-only">Section details</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const { ranking, view } = row;
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
                    <td className="px-3.5 py-3">
                      <CourseLink ranking={ranking} onOpenCourse={onOpenCourse} />
                      <span className="block max-w-[200px] text-xs text-slate">{ranking.course_title}</span>
                      {view.typeLabel ? <span className="block text-xs text-slate">{view.typeLabel}</span> : null}
                    </td>
                    <td className="px-3.5 py-3">
                      <Instructor view={view} />
                    </td>
                    <td className="px-3.5 py-3">
                      <Evidence view={view} />
                    </td>
                    <td className="px-3.5 py-3">
                      <Seats view={view} />
                    </td>
                    <td className="px-3.5 py-3">
                      <Schedule view={view} />
                    </td>
                    <td className="px-2 py-1.5">
                      <button
                        type="button"
                        onClick={() => toggle(ranking.crn)}
                        aria-expanded={isOpen}
                        aria-label={`Details for CRN ${ranking.crn}`}
                        className="flex h-10 w-10 items-center justify-center rounded-md hover:bg-wash"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#303434" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ transform: isOpen ? "rotate(180deg)" : undefined }}>
                          <path d="M6 9l6 6 6-6" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                  {isOpen ? (
                    <tr className="bg-[#FAFAF6]">
                      <td colSpan={7} className="px-3.5 pb-5 pt-1">
                        <SectionDetails row={row} />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      <ul className="flex flex-col gap-2.5 min-[1100px]:hidden">
        {rows.map((row) => {
          const { ranking, view } = row;
          const isOpen = open === ranking.crn;
          return (
            <li key={ranking.crn} className="flex flex-col gap-2 rounded-lg border border-line px-4 py-3.5 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2">
                  <span className="font-mono font-medium">{ranking.crn}</span>
                  <CopyCrnButton crn={ranking.crn} />
                </span>
                <span className="text-right"><Seats view={view} showOpen /></span>
              </div>
              <div className="min-w-0">
                <CourseLink ranking={ranking} onOpenCourse={onOpenCourse} />
                <span className="text-[13px] text-slate"> {ranking.course_title}</span>
                {view.typeLabel ? <span className="block text-xs text-slate">{view.typeLabel}</span> : null}
              </div>
              <Instructor view={view} />
              <Evidence view={view} />
              <Schedule view={view} />
              <button
                type="button"
                onClick={() => toggle(ranking.crn)}
                aria-expanded={isOpen}
                aria-label={`${isOpen ? "Hide" : "Show"} details for CRN ${ranking.crn}`}
                className="h-10 self-start rounded-md border border-silver bg-white px-3.5 text-sm font-semibold hover:bg-wash"
              >
                {isOpen ? "Hide details" : "Details"}
              </button>
              {isOpen ? <SectionDetails row={row} /> : null}
            </li>
          );
        })}
      </ul>
    </>
  );
}
