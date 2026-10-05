import { syntheticRankings } from "../fixtures/rankings";
import type { InstructorBreakdown, InstructorHistoryRow, SectionRanking } from "../types/rankings";

// Test-only builders over the synthetic fixtures. Names and numbers are invented.

export const historyRow = (
  name: string,
  aShare: number,
  effectiveN: number,
  overrides: Partial<InstructorHistoryRow> = {},
): InstructorHistoryRow => ({
  name,
  a_share: aShare,
  effective_n: effectiveN,
  term_count: 3,
  first_term: "202501",
  last_term: "202601",
  easiness_score: 8,
  scored: true,
  is_current: false,
  ...overrides,
});

export const breakdown = (overrides: Partial<InstructorBreakdown> = {}): InstructorBreakdown => ({
  status: "ready",
  instructors: [],
  current_instructor: null,
  current_instructor_has_history: false,
  other_instructor_count: 0,
  scoring_min_effective_n: 30,
  collapse_min_effective_n: 15,
  provenance: { freshness: "historical", source: "grade_distributions", source_term: "202601", detail: null },
  ...overrides,
});

/** A section whose current instructor has the given A share, or no history when share is null. */
export const section = (
  crn: string,
  instructor: string | null,
  share: number | null,
  overrides: Partial<SectionRanking> & { breakdown?: InstructorBreakdown | null; gradeCount?: number } = {},
): SectionRanking => {
  const base = structuredClone(syntheticRankings[0]);
  const { breakdown: breakdownOverride, gradeCount = 120, ...rest } = overrides;
  const instructors =
    share === null || instructor === null
      ? [historyRow("Other Teacher", 0.5, 200)]
      : [historyRow(instructor, share, gradeCount, { is_current: true, scored: gradeCount >= 30 }), historyRow("Other Teacher", 0.5, 200)];
  base.historical_analytics.instructor_breakdown =
    breakdownOverride === undefined
      ? breakdown({
          instructors,
          current_instructor: instructor,
          current_instructor_has_history: share !== null && instructor !== null,
        })
      : breakdownOverride;
  return {
    ...base,
    crn,
    subject: "ENC",
    course_number: "1101",
    course_title: "Composition I",
    instructor,
    gened_attributes: [{ code: "SGEC", label: "General Education Core Communication" }],
    ...rest,
  };
};
