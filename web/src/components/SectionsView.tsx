import { useMemo, useState, type ReactNode } from "react";

import type { Route } from "../lib/route";
import { sortSections, toRows, type SectionSort } from "../lib/section";
import type { SectionRanking } from "../types/rankings";
import { SectionTable } from "./SectionTable";
import { Notice } from "./Status";

export function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: ReactNode }) {
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

type Mode = "" | "in_person" | "hybrid" | "online";

const matchesMode = (delivery: string | null, mode: Mode): boolean => {
  if (mode === "") return true;
  if (mode === "in_person") return delivery === "In person";
  if (mode === "hybrid") return delivery === "Hybrid";
  return delivery === "Online" || delivery === "Mostly online";
};

/** A fully loaded set of sections with client-side filters and sorting. */
export function SectionsView({ sections, navigate }: { sections: SectionRanking[]; navigate: (route: Route) => void }) {
  const [sort, setSort] = useState<SectionSort>("course");
  const [hasHistory, setHasHistory] = useState(false);
  const [openSeats, setOpenSeats] = useState(false);
  const [mode, setMode] = useState<Mode>("");
  const toggleMode = (next: Mode) => setMode(mode === next ? "" : next);

  const all = useMemo(() => toRows(sections), [sections]);
  const rows = sortSections(
    all.filter(
      ({ view }) =>
        (!hasHistory || view.kind === "instructor" || view.kind === "thin") &&
        (!openSeats || (view.seatsOpen ?? 0) > 0) &&
        matchesMode(view.delivery, mode),
    ),
    sort,
  );

  return (
    <>
      <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter sections">
          <Chip on={hasHistory} onClick={() => setHasHistory(!hasHistory)}>Has grade history</Chip>
          <Chip on={openSeats} onClick={() => setOpenSeats(!openSeats)}>Open seats</Chip>
          <Chip on={mode === "in_person"} onClick={() => toggleMode("in_person")}>In person</Chip>
          <Chip on={mode === "hybrid"} onClick={() => toggleMode("hybrid")}>Hybrid</Chip>
          <Chip on={mode === "online"} onClick={() => toggleMode("online")}>Online</Chip>
        </div>
        {/* Wide screens sort from the table headers; phones have no headers to click. */}
        <label className="flex items-center gap-2 text-sm text-slate min-[1100px]:hidden">
          Sort
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as SectionSort)}
            className="h-9 rounded-md border border-silver bg-white px-2 text-sm text-ink"
          >
            <option value="course">Course</option>
            <option value="a_share">Most A's</option>
            <option value="seats">Most seats open</option>
            <option value="schedule">Schedule</option>
            <option value="crn">CRN</option>
          </select>
        </label>
      </div>
      {rows.length === 0 ? (
        <Notice title="No sections match these filters">Turn a filter off to see more sections.</Notice>
      ) : (
        <SectionTable
          rows={rows}
          sort={sort}
          onSort={setSort}
          onOpenCourse={(subject, courseNumber) => navigate({ view: "search", q: `${subject} ${courseNumber}` })}
        />
      )}
      <p className="mt-3 text-sm text-slate" role="status">
        Showing {rows.length} of {all.length} {all.length === 1 ? "section" : "sections"}
      </p>
    </>
  );
}
