import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";
import { RankingTable } from "./RankingTable";
import { syntheticRankings } from "../fixtures/rankings";
import type { SectionRanking } from "../types/rankings";

/**
 * Renders a single ranking, expanded, inside the real RankingTable so both
 * the desktop row and the mobile card render together (jsdom does not honor
 * the Tailwind lg: breakpoint classes that hide one layout at a time).
 */
const renderExpanded = (ranking: SectionRanking) => {
  render(
    <RankingTable
      rankings={[ranking]}
      rankOffset={0}
      expandedCrn={ranking.crn}
      onToggle={() => {}}
    />,
  );
  return {
    table: screen.getByRole("table"),
    cardContainer: screen.getByLabelText("Course ranking cards"),
    detailRegions: screen.getAllByRole("region", { name: /^Details for/ }),
  };
};

test("course with effective_n=0 (D-21 non-letter-grade exception) reads as a prior everywhere", () => {
  const ranking: SectionRanking = {
    ...syntheticRankings[4], // BSC 1005, base course fixture (effective_n 342 normally)
    crn: "49001",
    subject: "IDS",
    score_source: "course",
    effective_n: 0,
  };
  const { table, cardContainer, detailRegions } = renderExpanded(ranking);

  const note = "No letter-grade history (pass/fail or independent study) — score is a prior";
  expect(within(table).getByText(note)).toBeVisible();
  expect(within(cardContainer).getByText(note)).toBeVisible();

  expect(detailRegions).toHaveLength(2);
  detailRegions.forEach((region) => {
    expect(
      within(region).getByText("No letter-grade history (pass/fail or independent study)"),
    ).toBeVisible();
    expect(within(region).getByText("No letter grades")).toBeVisible();
  });

  // No surface may claim course-level history, a 0-grades sample, or the
  // course-history low-confidence explanation for this scope (D-20).
  expect(screen.queryAllByText("Course-level history")).toHaveLength(0);
  expect(screen.queryAllByText(/^0 grades$/)).toHaveLength(0);
  expect(
    screen.queryByRole("button", { name: "Based on limited historical data." }),
  ).not.toBeInTheDocument();

  // The numeric easiness score is unchanged and still rendered.
  expect(screen.getAllByText(ranking.easiness_score.toFixed(1)).length).toBeGreaterThan(0);
});

const GLOBAL_NOTE = "No historical grades for this course — score is a global prior";
const GLOBAL_SOURCE = "Global prior — no course evidence";
const GLOBAL_SAMPLE = "No course grades";
const GLOBAL_SUMMARY =
  "No historical grade data exists for this course; the score is a global prior, not this course's outcome.";

const assertNoCourseEvidence = (ranking: SectionRanking) => {
  const { table, cardContainer, detailRegions } = renderExpanded(ranking);

  expect(within(table).getByText(GLOBAL_NOTE)).toBeVisible();
  expect(within(cardContainer).getByText(GLOBAL_NOTE)).toBeVisible();
  expect(detailRegions).toHaveLength(2);
  detailRegions.forEach((region) => {
    expect(within(region).getByText(GLOBAL_SOURCE)).toBeVisible();
    expect(within(region).getByText(GLOBAL_SAMPLE)).toBeVisible();
    expect(within(region).getByText(GLOBAL_SUMMARY)).toBeVisible();
  });
  expect(screen.queryAllByText("Course-level history")).toHaveLength(0);
  expect(screen.queryAllByText(/^0 grades$/)).toHaveLength(0);
  expect(screen.queryAllByText(/^22 grades$/)).toHaveLength(0);
};

test("no_course_evidence: global with effective_n=0 shows the global-prior wording, never course-level history", () => {
  const ranking: SectionRanking = { ...syntheticRankings[6], crn: "49010", effective_n: 0 };
  assertNoCourseEvidence(ranking);
});

test("no_course_evidence: global with effective_n=22 (fixture CRN 17205) shows the global-prior wording, never course-level history", () => {
  assertNoCourseEvidence(syntheticRankings[6]);
});

test("no_course_evidence: subject with effective_n=0 falls closed to the global-prior wording", () => {
  const ranking: SectionRanking = {
    ...syntheticRankings[6],
    crn: "49011",
    score_source: "subject",
    subject: "PSY",
    effective_n: 0,
  };
  assertNoCourseEvidence(ranking);
});

test("subject_fallback: subject with effective_n=45 names the subject and never claims course history", () => {
  const ranking: SectionRanking = {
    ...syntheticRankings[6],
    crn: "49012",
    score_source: "subject",
    subject: "PSY",
    effective_n: 45,
  };
  const { table, cardContainer, detailRegions } = renderExpanded(ranking);

  const note = "No course history — score uses PSY subject-level history";
  expect(within(table).getByText(note)).toBeVisible();
  expect(within(cardContainer).getByText(note)).toBeVisible();
  expect(detailRegions).toHaveLength(2);
  detailRegions.forEach((region) => {
    expect(within(region).getByText("Subject-level fallback")).toBeVisible();
    expect(within(region).getByText("45 subject-level grades")).toBeVisible();
    expect(
      within(region).getByText(
        "This course has no own grade history; the score uses PSY subject-level history, not this course's grade distribution.",
      ),
    ).toBeVisible();
  });
  expect(screen.queryAllByText("Course-level history")).toHaveLength(0);
  expect(screen.queryAllByText(/^0 grades$/)).toHaveLength(0);
});

test("course_history: course with effective_n=342 (fixture CRN 15502) keeps the existing wording and shows no evidence note", () => {
  const ranking = syntheticRankings[4]; // BSC 1005, course, effective_n 342
  const { table, cardContainer, detailRegions } = renderExpanded(ranking);

  expect(detailRegions).toHaveLength(2);
  detailRegions.forEach((region) => {
    expect(within(region).getByText("Course-level history")).toBeVisible();
    expect(within(region).getByText("342 grades")).toBeVisible();
    expect(within(region).getByText(/^Historical analytics cover /)).toBeVisible();
  });
  // No evidence note anywhere for a real course-history row/card.
  expect(
    screen.queryByText(
      "No historical grades for this course — score is a global prior",
    ),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByText("No letter-grade history (pass/fail or independent study) — score is a prior"),
  ).not.toBeInTheDocument();
  expect(within(table).getByText(ranking.easiness_score.toFixed(1))).toBeVisible();
  expect(within(cardContainer).getByText(ranking.easiness_score.toFixed(1))).toBeVisible();
});

test("course_history: instructor_course with effective_n=34 and low confidence (fixture CRN 16880) keeps the limited-data explanation", () => {
  const ranking = syntheticRankings[5]; // AMH 2020, instructor_course, effective_n 34, low confidence
  const { detailRegions } = renderExpanded(ranking);

  expect(detailRegions).toHaveLength(2);
  detailRegions.forEach((region) => {
    expect(within(region).getByText("Instructor + course history")).toBeVisible();
    expect(within(region).getByText("34 grades")).toBeVisible();
    expect(within(region).getByText("Based on limited historical data.")).toBeVisible();
  });
  expect(
    screen.getAllByRole("button", { name: "Based on limited historical data." }).length,
  ).toBeGreaterThan(0);
});

test("no_course_evidence: an unrecognized score_source fails closed and never claims course history", () => {
  const ranking = {
    ...syntheticRankings[6],
    crn: "49013",
    score_source: "unheard_of_source" as unknown as SectionRanking["score_source"],
    effective_n: 10,
  } as SectionRanking;
  assertNoCourseEvidence(ranking);
});
