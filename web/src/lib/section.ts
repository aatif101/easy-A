import type { InstructorHistoryRow, Meeting, SectionRanking } from "../types/rankings";

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

export interface GradeShares {
  a: number;
  b: number;
  c: number;
  d: number;
  f: number;
}

export interface SectionView {
  kind: EvidenceKind;
  aShare: number | null;
  /** Null when only the A share is known (a cache row written before the others existed). */
  grades: GradeShares | null;
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
  waitSeats: number | null;
  seatsStale: boolean;
  typeLabel: string | null;
  schedule: string[];
  /** Minutes after midnight of the first class meeting, for sorting. */
  firstStart: number | null;
  sectionLine: string | null;
  meetingDetails: string[];
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

export const gradeShares = (row: InstructorHistoryRow): GradeShares | null => {
  const { a_share: a, b_share: b, c_share: c, d_share: d, f_share: f } = row;
  return b == null || c == null || d == null || f == null ? null : { a, b, c, d, f };
};

const clock = (value: string): { text: string; suffix: string } => {
  const [hours, minutes] = value.split(":").map(Number);
  return { text: `${hours % 12 || 12}:${String(minutes).padStart(2, "0")}`, suffix: hours < 12 ? "am" : "pm" };
};

const timeRange = (meeting: Meeting): string | null => {
  if (!meeting.start_time || !meeting.end_time) return null;
  const start = clock(meeting.start_time);
  const end = clock(meeting.end_time);
  return `${start.text}${start.suffix === end.suffix ? "" : start.suffix}–${end.text}${end.suffix}`;
};

const isRealDay = (days: string): boolean => !/^(tba|arr)$/i.test(days);

const meetingText = (meeting: Meeting): string => [meeting.days, timeRange(meeting)].filter(Boolean).join(" ");

/** Class meetings only: exams live in the details. Days without a known time share one line. */
const scheduleLines = (meetings: Meeting[], delivery: string | null): string[] => {
  const classes = meetings.filter((meeting) => !meeting.is_exam && isRealDay(meeting.days));
  const timed = classes.filter(timeRange);
  const untimed = classes.filter((meeting) => !timeRange(meeting)).map((meeting) => meeting.days);
  const lines = [...new Set(timed.map(meetingText))];
  if (untimed.length) lines.push([...new Set(untimed)].join(", "));
  if (lines.length) return lines;
  return [delivery === "Online" || delivery === "Mostly online" ? "No set meeting time" : "Time not listed"];
};

const firstStartMinutes = (meetings: Meeting[]): number | null => {
  const start = meetings.find((meeting) => !meeting.is_exam && meeting.start_time)?.start_time;
  if (!start) return null;
  const [hours, minutes] = start.split(":").map(Number);
  return hours * 60 + minutes;
};

const creditsText = (credits: string): string => `${credits} ${credits === "1" ? "credit" : "credits"}`;

const placeText = (meeting: Meeting): string | null => {
  const parts = [meeting.building, meeting.room].filter((part) => part && !/^tbat?$/i.test(part));
  return parts.length ? parts.join(" ") : null;
};

const meetingDetail = (meeting: Meeting): string =>
  meeting.is_exam
    ? `Exam: ${meetingText(meeting)}`
    : [meetingText(meeting), placeText(meeting)].filter(Boolean).join(" · ");

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
    caption = "Professor not assigned yet";
  } else {
    kind = "no_history";
    caption = "No past grades for this professor here";
  }

  const seats = ranking.seats;
  const delivery = deliveryLabel(ranking.modality.delivery_method);
  const meetings = ranking.meetings ?? [];
  const sectionType = ranking.section_type ?? null;
  return {
    kind,
    aShare: current ? current.a_share : null,
    grades: current ? gradeShares(current) : null,
    gradeCount: current ? current.effective_n : null,
    termCount: current ? current.term_count : null,
    caption,
    instructor: named ?? "Not assigned",
    instructorNamed: named !== null,
    rmpLinkable: named !== null && ranking.instructor_provenance.freshness !== "unavailable",
    subject: ranking.subject,
    delivery,
    seatsOpen: seats.seats_remaining ?? ranking.seats_remaining,
    seatsCapacity: seats.capacity,
    waitSeats: seats.wait_seats_available,
    seatsStale: seats.freshness === "stale",
    typeLabel: sectionType === "Laboratory" ? "Lab" : sectionType === "Class Lecture" ? null : sectionType,
    schedule: scheduleLines(meetings, delivery),
    firstStart: firstStartMinutes(meetings),
    sectionLine:
      [
        ranking.section_number ? `Section ${ranking.section_number}` : null,
        ranking.credits ? creditsText(ranking.credits) : null,
        sectionType,
      ]
        .filter(Boolean)
        .join(" · ") || null,
    meetingDetails: meetings.filter((meeting) => isRealDay(meeting.days)).map(meetingDetail),
    history: breakdown?.status === "lab_section" ? [] : breakdown?.instructors ?? [],
    otherInstructorCount: breakdown?.other_instructor_count ?? 0,
  };
};

export interface SectionRow {
  ranking: SectionRanking;
  view: SectionView;
}

export const toRows = (items: SectionRanking[]): SectionRow[] =>
  items.map((ranking) => ({ ranking, view: toSectionView(ranking) }));

export const formatShare = (share: number): string => `${Math.round(share * 100)}%`;

export const seatsText = (view: SectionView): string => {
  if (view.seatsOpen === null) return "—";
  if (view.seatsOpen <= 0) return "Full";
  return view.seatsCapacity === null ? `${view.seatsOpen}` : `${view.seatsOpen} of ${view.seatsCapacity}`;
};

/** Only a full class needs this: it is how a student can still get in line. */
export const waitlistText = (view: SectionView): string | null =>
  view.seatsOpen !== null && view.seatsOpen <= 0 && (view.waitSeats ?? 0) > 0
    ? `${view.waitSeats} waitlist ${view.waitSeats === 1 ? "spot" : "spots"}`
    : null;

const KIND_ORDER: Record<EvidenceKind, number> = {
  instructor: 0,
  thin: 1,
  no_history: 2,
  unnamed: 2,
  lab: 3,
  none: 3,
};

export type SectionSort = "course" | "a_share" | "seats" | "schedule" | "crn";

/** Most A's first, but only among real instructor history; thin and missing evidence go after. */
export const sortSections = <Row extends { ranking: SectionRanking; view: SectionView }>(
  rows: Row[],
  sort: SectionSort,
): Row[] =>
  rows.toSorted((left, right) => {
    if (sort === "crn") return left.ranking.crn.localeCompare(right.ranking.crn);
    if (sort === "course") {
      return (
        left.ranking.subject.localeCompare(right.ranking.subject) ||
        left.ranking.course_number.localeCompare(right.ranking.course_number) ||
        left.ranking.crn.localeCompare(right.ranking.crn)
      );
    }
    if (sort === "schedule") {
      return (
        (left.view.firstStart ?? Infinity) - (right.view.firstStart ?? Infinity) ||
        left.ranking.crn.localeCompare(right.ranking.crn)
      );
    }
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
