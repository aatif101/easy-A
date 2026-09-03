import type {
  ConfidenceLabel,
  RankingSignal,
  RankingSort,
  SectionRanking,
} from "../types/rankings";

export interface RankingFilters {
  subject: string;
  courseSearch: string;
  genedCode: string;
  deliveryMethod: string;
  openSeatsOnly: boolean;
  minimumEasiness: number;
  confidence: "all" | ConfidenceLabel;
  sort: RankingSort;
}

export const initialFilters: RankingFilters = {
  subject: "",
  courseSearch: "",
  genedCode: "",
  deliveryMethod: "",
  openSeatsOnly: false,
  minimumEasiness: 0,
  confidence: "all",
  sort: "easiness_desc",
};

export interface ParsedCourseSearch {
  subject?: string;
  courseNumber?: string;
}

export const parseCourseSearch = (value: string): ParsedCourseSearch => {
  const normalized = value.trim().toUpperCase();
  if (!normalized) return {};
  const combined = normalized.match(/^([A-Z]{2,4})\s*-?\s*([0-9][0-9A-Z]{2,4})$/);
  if (combined) return { subject: combined[1], courseNumber: combined[2] };
  if (/^[A-Z]{2,4}$/.test(normalized)) return { subject: normalized };
  if (/^[0-9][0-9A-Z]{2,4}$/.test(normalized)) return { courseNumber: normalized };
  return {};
};

export const hasActiveFilters = (filters: RankingFilters): boolean =>
  filters.subject !== "" ||
  filters.courseSearch.trim() !== "" ||
  filters.genedCode !== "" ||
  filters.deliveryMethod !== "" ||
  filters.openSeatsOnly ||
  filters.minimumEasiness > 0 ||
  filters.confidence !== "all";

export const formatPercent = (value: number): string => `${(value * 100).toFixed(1)}%`;

const signalLabels: Record<string, string> = {
  "attendance:required": "Attendance required",
  "attendance:not_required": "Attendance not required",
  "exam_location:in_person": "In-person exams",
  "exam_location:online": "Online exams",
  "exam_location:mixed": "Mixed exam format",
  "lab:required": "SMART Lab",
  "late_work:not_allowed": "No late work",
  "late_work:allowed": "Late work allowed",
  "participation:required": "Participation required",
  "curve:present": "Curve noted",
  "curve:not_present": "No curve",
  "quiz:present": "Quizzes",
};

export const signalLabel = (signal: RankingSignal): string => {
  const key = `${signal.signal_type}:${signal.value}`;
  return (
    signalLabels[key] ??
    `${signal.signal_type.replaceAll("_", " ")} · ${signal.value.replaceAll("_", " ")}`
  );
};

export const scoreSourceLabel = (source: SectionRanking["score_source"]): string => {
  const labels: Record<SectionRanking["score_source"], string> = {
    instructor_course: "Instructor + course history",
    course: "Course-level history",
    subject: "Subject-level fallback",
    global: "Global fallback",
  };
  return labels[source];
};

export const instructorLabel = (ranking: SectionRanking): string => {
  const instructor = ranking.instructor?.trim();
  if (instructor) return instructor;
  const detail = ranking.instructor_provenance.detail?.toLowerCase() ?? "";
  if (detail.includes("ambiguous")) return "Ambiguous / unavailable";
  if (detail.includes("blank") || ranking.instructor_provenance.freshness === "current") {
    return "Staff";
  }
  return "Unknown";
};

export const seatSourceLabel = (ranking: SectionRanking): string => {
  if (ranking.seats.provenance.freshness === "unavailable") return "Seat data unavailable";
  if (ranking.seats.provenance.source === "seat_snapshots") {
    return "Latest observed seat data · seat snapshot";
  }
  return "Latest observed seat data · stored section record";
};

export const signalSourceLabel = (ranking: SectionRanking): string => {
  if (ranking.signal_provenance.freshness === "historical") {
    return "Historical syllabus reference";
  }
  if (ranking.signal_provenance.freshness === "unavailable") {
    return "No policy information available";
  }
  if (ranking.signal_provenance.source === "schedule_section_note") {
    return "Current section note";
  }
  return "Current syllabus";
};
