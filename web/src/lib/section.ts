import type { InstructorHistoryRow, SectionRanking } from "../types/rankings";

/**
 * What the grade evidence for one section actually is. Only "instructor" and "thin" carry an
 * A share, and it is always this section's instructor in this course, never a course average.
 */
export type EvidenceKind =
  | "instructor"
  | "thin"
  | "unnamed"
  | "no_history"
  | "lab"
  | "none";

export interface SectionView {
  kind: EvidenceKind;
  aShare: number | null;
  gradeCount: number | null;
  termCount: number | null;
  caption: string;
  instructor: string;
  instructorNamed: boolean;
  /** Named, and the current assignment is known (not an unavailable or ambiguous state). */
  rmpLinkable: boolean;
  subject: string;
  delivery: string | null;
  seatsOpen: number | null;
  seatsCapacity: number | null;
  seatsStale: boolean;
  history: InstructorHistoryRow[];
  otherInstructorCount: number;
}

const DELIVERY_LABELS: Record<string, string> = {
  CL: "In person",
  HB: "Hybrid",
  PD: "Mostly online",
  AD: "Online",
};

export const deliveryLabel = (code: string | null): string | null =>
  code ? DELIVERY_LABELS[code] ?? code : null;

const isPlaceholderName = (name: string | null): boolean =>
  !name || /^(staff|tba|tbd)$/i.test(name.trim());

const plural = (count: number, word: string): string =>
  `${count.toLocaleString("en-US")} ${word}${count === 1 ? "" : "s"}`;

export const toSectionView = (ranking: SectionRanking): SectionView => {
  const breakdown = ranking.historical_analytics.instructor_breakdown ?? null;
  const namedFromBreakdown = breakdown?.current_instructor ?? null;
  const named = namedFromBreakdown ?? (isPlaceholderName(ranking.instructor) ? null : ranking.instructor);
  const current = breakdown?.instructors.find((row) => row.is_current) ?? null;

  let kind: EvidenceKind;
  let caption: string;
  if (!breakdown) {
    kind = "none";
    caption = "No grade history for this course";
  } else if (breakdown.status === "lab_section") {
    kind = "lab";
    caption = "Lab section, no letter grades";
  } else if (current) {
    kind = current.scored ? "instructor" : "thin";
    caption = current.scored
      ? `${plural(current.effective_n, "grade")} · ${plural(current.term_count, "term")}`
      : `${plural(current.effective_n, "grade")} · too few to trust`;
  } else if (!named) {
    kind = "unnamed";
    caption = "Instructor not announced yet";
  } else {
    kind = "no_history";
    caption = "No history for this instructor here";
  }

  const seats = ranking.seats;
  return {
    kind,
    aShare: current ? current.a_share : null,
    gradeCount: current ? current.effective_n : null,
    termCount: current ? current.term_count : null,
    caption,
    instructor: named ?? "TBA",
    instructorNamed: named !== null,
    rmpLinkable: named !== null && ranking.instructor_provenance.freshness !== "unavailable",
    subject: ranking.subject,
    delivery: deliveryLabel(ranking.modality.delivery_method),
    seatsOpen: seats.seats_remaining ?? ranking.seats_remaining,
    seatsCapacity: seats.capacity,
    seatsStale: seats.freshness === "stale",
    history: breakdown?.status === "lab_section" ? [] : breakdown?.instructors ?? [],
    otherInstructorCount: breakdown?.other_instructor_count ?? 0,
  };
};

export const formatShare = (share: number): string => `${Math.round(share * 100)}%`;

export const seatsText = (view: SectionView): string => {
  if (view.seatsOpen === null) return "—";
  if (view.seatsOpen <= 0) return "Full";
  return view.seatsCapacity === null ? `${view.seatsOpen}` : `${view.seatsOpen}/${view.seatsCapacity}`;
};

const KIND_ORDER: Record<EvidenceKind, number> = {
  instructor: 0,
  thin: 1,
  no_history: 2,
  unnamed: 2,
  lab: 3,
  none: 3,
};

export type SectionSort = "a_share" | "seats" | "crn";

/** Most A's first, but only among real instructor history; thin and missing evidence go after. */
export const sortSections = <Row extends { ranking: SectionRanking; view: SectionView }>(
  rows: Row[],
  sort: SectionSort,
): Row[] =>
  rows.toSorted((left, right) => {
    if (sort === "crn") return left.ranking.crn.localeCompare(right.ranking.crn);
    if (sort === "seats") {
      return (right.view.seatsOpen ?? -1) - (left.view.seatsOpen ?? -1) ||
        left.ranking.crn.localeCompare(right.ranking.crn);
    }
    return (
      KIND_ORDER[left.view.kind] - KIND_ORDER[right.view.kind] ||
      (right.view.aShare ?? -1) - (left.view.aShare ?? -1) ||
      left.ranking.crn.localeCompare(right.ranking.crn)
    );
  });

const SEASONS: Record<string, string> = { "01": "Spring", "05": "Summer", "08": "Fall" };

export const termName = (code: string): string => {
  const season = SEASONS[code.slice(4)];
  return season ? `${season} ${code.slice(0, 4)}` : code;
};

export const termSpan = (first: string, last: string): string =>
  first === last ? termName(first) : `${termName(first)} – ${termName(last)}`;
