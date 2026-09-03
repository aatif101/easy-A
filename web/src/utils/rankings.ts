import type { ConfidenceLabel, RankingSignal, SectionRanking } from "../types/rankings";

export interface RankingFilters {
  search: string;
  gened: "all" | "yes" | "no";
  modality: "all" | "classroom" | "hybrid" | "online";
  openSeatsOnly: boolean;
  minimumEasiness: number;
  confidence: "all" | ConfidenceLabel;
  sort: "easiness" | "withdrawal" | "seats" | "course";
}

export const initialFilters: RankingFilters = {
  search: "",
  gened: "all",
  modality: "all",
  openSeatsOnly: false,
  minimumEasiness: 0,
  confidence: "all",
  sort: "easiness",
};

const modalityGroup = (ranking: SectionRanking): Exclude<RankingFilters["modality"], "all"> => {
  const method = ranking.modality.delivery_method;
  if (method === "AD" || method === "PD") return "online";
  if (method === "HB") return "hybrid";
  return "classroom";
};

export const filterAndSortRankings = (
  rankings: SectionRanking[],
  filters: RankingFilters,
): SectionRanking[] => {
  const search = filters.search.trim().toLocaleLowerCase();
  const filtered = rankings.filter((ranking) => {
    const searchable = [
      ranking.subject,
      ranking.course_number,
      ranking.course_title,
      ranking.instructor ?? "Staff",
      ranking.crn,
    ]
      .join(" ")
      .toLocaleLowerCase();
    return (
      (!search || searchable.includes(search)) &&
      (filters.gened === "all" ||
        (filters.gened === "yes") === (ranking.gened_attributes.length > 0)) &&
      (filters.modality === "all" || modalityGroup(ranking) === filters.modality) &&
      (!filters.openSeatsOnly || (ranking.seats_remaining ?? 0) > 0) &&
      ranking.easiness_score >= filters.minimumEasiness &&
      (filters.confidence === "all" || ranking.confidence_label === filters.confidence)
    );
  });

  return filtered.toSorted((left, right) => {
    if (filters.sort === "withdrawal") {
      return left.smoothed_withdrawal_rate - right.smoothed_withdrawal_rate;
    }
    if (filters.sort === "seats") {
      return (right.seats_remaining ?? -1) - (left.seats_remaining ?? -1);
    }
    if (filters.sort === "course") {
      return `${left.subject} ${left.course_number}`.localeCompare(
        `${right.subject} ${right.course_number}`,
      );
    }
    return right.easiness_score - left.easiness_score;
  });
};

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
