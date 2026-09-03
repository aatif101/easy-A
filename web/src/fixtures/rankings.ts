import type {
  ConfidenceLabel,
  Freshness,
  RankingProvenance,
  RankingSignal,
  ScoreSource,
  SectionRanking,
} from "../types/rankings";

// Synthetic frontend-only fixtures. These do not describe real students or sections.
export const SYNTHETIC_FIXTURE_NOTICE = "Showing synthetic demonstration data";

const current = (source: string): RankingProvenance => ({
  freshness: "current",
  source,
  source_term: "202701",
  detail: null,
});

const historical = (source: string, term = "202608"): RankingProvenance => ({
  freshness: "historical",
  source,
  source_term: term,
  detail: "Synthetic historical reference",
});

const unavailable: RankingProvenance = {
  freshness: "unavailable",
  source: "unavailable",
  source_term: null,
  detail: null,
};

interface FixtureOptions {
  crn: string;
  subject: string;
  courseNumber: string;
  courseTitle: string;
  instructor: string | null;
  modality: string;
  deliveryMethod: string;
  seatsRemaining: number | null;
  capacity?: number;
  easiness: number;
  withdrawalRate: number;
  confidence: ConfidenceLabel;
  effectiveN: number;
  scoreSource: ScoreSource;
  gened?: { code: string; label: string }[];
  signals?: RankingSignal[];
  signalProvenance?: RankingProvenance;
}

const makeSignal = (
  signalType: string,
  value: string,
  evidence: string,
  source: string,
  freshness: Freshness,
  sourceTerm = "202701",
): RankingSignal => ({
  signal_type: signalType,
  value,
  confidence: freshness === "historical" ? 0.85 : 0.97,
  source,
  source_identifier: `synthetic:${signalType}`,
  source_term: sourceTerm,
  freshness,
  evidence,
});

const makeRanking = (options: FixtureOptions): SectionRanking => {
  const capacity = options.capacity ?? 30;
  const enrollment =
    options.seatsRemaining === null ? null : capacity - options.seatsRemaining;
  const analyticsProvenance = historical("grade_distributions", "202608");
  return {
    term: "202701",
    term_name: "Spring 2027",
    crn: options.crn,
    subject: options.subject,
    course_number: options.courseNumber,
    course_title: options.courseTitle,
    instructor: options.instructor,
    instructor_provenance: current("section_instructors"),
    modality: {
      delivery_method: options.deliveryMethod,
      delivery_label: options.modality,
      provenance: current("sections.delivery_method"),
    },
    seats_remaining: options.seatsRemaining,
    seats: {
      capacity: options.seatsRemaining === null ? null : capacity,
      enrollment,
      seats_remaining: options.seatsRemaining,
      wait_seats_available: options.seatsRemaining === null ? null : 0,
      provenance: current("seat_snapshots"),
    },
    gened_attributes: options.gened ?? [],
    gened_provenance: options.gened?.length
      ? current("course_attributes")
      : unavailable,
    easiness_score: options.easiness,
    smoothed_withdrawal_rate: options.withdrawalRate,
    confidence_label: options.confidence,
    effective_n: options.effectiveN,
    score_source: options.scoreSource,
    historical_analytics: {
      easiness_score: options.easiness,
      smoothed_withdrawal_rate: options.withdrawalRate,
      confidence_label: options.confidence,
      effective_n: options.effectiveN,
      score_source: options.scoreSource,
      prior_level: options.scoreSource === "global" ? "global" : "course",
      completed_grade_count: Math.round(options.effectiveN),
      total_grade_count: Math.round(options.effectiveN * 1.06),
      withdrawal_count: Math.round(options.effectiveN * options.withdrawalRate),
      section_count: Math.max(1, Math.round(options.effectiveN / 32)),
      term_count: options.confidence === "low" ? 1 : 3,
      mapped_instructor_section_count:
        options.scoreSource === "instructor_course" ? 4 : 0,
      provenance: analyticsProvenance,
    },
    signals: options.signals ?? [],
    signal_provenance: options.signalProvenance ?? unavailable,
    section_provenance: current("sections"),
  };
};

const currentNoteSignals = [
  makeSignal(
    "exam_location",
    "in_person",
    "Quizzes and exams must be completed in person in the SMART Lab.",
    "schedule_section_note",
    "current",
  ),
  makeSignal(
    "lab",
    "required",
    "Students must spend two hours each week in the SMART Lab.",
    "schedule_section_note",
    "current",
  ),
];

const currentSyllabusSignals = [
  makeSignal(
    "attendance",
    "required",
    "Attendance is required and will be recorded each class meeting.",
    "current_term_syllabus",
    "current",
  ),
];

const historicalSignals = [
  makeSignal(
    "late_work",
    "not_allowed",
    "Late work was not accepted after the posted deadline.",
    "historical_same_instructor_course",
    "historical",
    "202608",
  ),
];

export const syntheticRankings: SectionRanking[] = [
  makeRanking({
    crn: "19410",
    subject: "MAC",
    courseNumber: "1105",
    courseTitle: "College Algebra",
    instructor: null,
    modality: "Hybrid Blend 50–79%",
    deliveryMethod: "HB",
    seatsRemaining: 12,
    capacity: 135,
    easiness: 7.4,
    withdrawalRate: 0.086,
    confidence: "medium",
    effectiveN: 142,
    scoreSource: "course",
    gened: [{ code: "SMEL", label: "Enhanced General Education Mathematics" }],
    signals: currentNoteSignals,
    signalProvenance: current("schedule_section_note"),
  }),
  makeRanking({
    crn: "19411",
    subject: "MAC",
    courseNumber: "1105",
    courseTitle: "College Algebra",
    instructor: "Leslaw Skrzypek",
    modality: "Classroom 1–49%",
    deliveryMethod: "CL",
    seatsRemaining: 4,
    easiness: 8.7,
    withdrawalRate: 0.041,
    confidence: "high",
    effectiveN: 286,
    scoreSource: "instructor_course",
    gened: [{ code: "SMEL", label: "Enhanced General Education Mathematics" }],
    signals: currentSyllabusSignals,
    signalProvenance: current("current_term_syllabus"),
  }),
  makeRanking({
    crn: "14022",
    subject: "ENC",
    courseNumber: "1101",
    courseTitle: "Composition I",
    instructor: "Jordan Alvarez",
    modality: "Classroom 1–49%",
    deliveryMethod: "CL",
    seatsRemaining: 8,
    easiness: 8.1,
    withdrawalRate: 0.052,
    confidence: "medium",
    effectiveN: 126,
    scoreSource: "instructor_course",
    gened: [{ code: "COMM", label: "Communication" }],
    signals: historicalSignals,
    signalProvenance: historical("historical_same_instructor_course"),
  }),
  makeRanking({
    crn: "14023",
    subject: "ENC",
    courseNumber: "1101",
    courseTitle: "Composition I",
    instructor: "Maya Chen",
    modality: "All Online 100%",
    deliveryMethod: "AD",
    seatsRemaining: 3,
    easiness: 7.8,
    withdrawalRate: 0.064,
    confidence: "medium",
    effectiveN: 118,
    scoreSource: "instructor_course",
    gened: [{ code: "COMM", label: "Communication" }],
  }),
  makeRanking({
    crn: "15502",
    subject: "BSC",
    courseNumber: "1005",
    courseTitle: "Biological Principles for Non-Majors",
    instructor: "Priya Nair",
    modality: "Classroom 1–49%",
    deliveryMethod: "CL",
    seatsRemaining: 0,
    easiness: 6.9,
    withdrawalRate: 0.102,
    confidence: "high",
    effectiveN: 342,
    scoreSource: "course",
    gened: [{ code: "SCIV", label: "Natural Sciences" }],
  }),
  makeRanking({
    crn: "16880",
    subject: "AMH",
    courseNumber: "2020",
    courseTitle: "American History II",
    instructor: "Taylor Brooks",
    modality: "All Online 100%",
    deliveryMethod: "AD",
    seatsRemaining: 19,
    easiness: 9.1,
    withdrawalRate: 0.028,
    confidence: "low",
    effectiveN: 34,
    scoreSource: "instructor_course",
    gened: [{ code: "HUMA", label: "Humanities" }],
  }),
  makeRanking({
    crn: "17205",
    subject: "PSY",
    courseNumber: "2012",
    courseTitle: "Introduction to Psychological Science",
    instructor: "Sam Rivera",
    modality: "Primarily DL 80–99%",
    deliveryMethod: "PD",
    seatsRemaining: null,
    easiness: 6.4,
    withdrawalRate: 0.12,
    confidence: "low",
    effectiveN: 22,
    scoreSource: "global",
  }),
];
