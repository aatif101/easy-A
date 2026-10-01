import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";
import { RankingTable } from "./RankingTable";
import { syntheticRankings } from "../fixtures/rankings";
import type {
  InstructorBreakdown,
  InstructorHistoryRow,
  SectionRanking,
} from "../types/rankings";

const CAVEAT =
  "USF lists one instructor per section; co-taught courses are attributed to the listed instructor.";

/**
 * Renders a single ranking, expanded, inside the real RankingTable so both the
 * desktop row and the mobile card render together (same pattern as
 * RankingEvidence.test.tsx).
 */
const renderExpanded = (ranking: SectionRanking) => {
  render(
    <RankingTable rankings={[ranking]} rankOffset={0} expandedCrn={ranking.crn} onToggle={() => {}} />,
  );
  return {
    detailRegions: screen.getAllByRole("region", { name: /^Details for/ }),
  };
};

const row = (overrides: Partial<InstructorHistoryRow> & { name: string }): InstructorHistoryRow => ({
  a_share: 0.3,
  effective_n: 100,
  term_count: 3,
  first_term: "202501",
  last_term: "202601",
  easiness_score: 6.5,
  scored: true,
  is_current: false,
  ...overrides,
});

const makeBreakdown = (overrides: Partial<InstructorBreakdown> = {}): InstructorBreakdown => ({
  status: "ready",
  instructors: [
    row({ name: "X. Ou", a_share: 0.4, effective_n: 175, easiness_score: 6.1, is_current: true }),
    row({ name: "J. Ligatti", a_share: 0.251, effective_n: 203 }),
  ],
  current_instructor: "X. Ou",
  current_instructor_has_history: true,
  other_instructor_count: 0,
  scoring_min_effective_n: 30,
  collapse_min_effective_n: 15,
  provenance: {
    freshness: "historical",
    source: "grade_distributions",
    source_term: "202601",
    detail: null,
  },
  ...overrides,
});

const withBreakdown = (
  breakdown: InstructorBreakdown | null,
  overrides: Partial<SectionRanking> = {},
): SectionRanking => {
  const base: SectionRanking = {
    ...syntheticRankings[4], // BSC 1005, course, effective_n 342
    crn: "49100",
    instructor: "X. Ou",
    ...overrides,
  };
  return {
    ...base,
    historical_analytics: { ...base.historical_analytics, instructor_breakdown: breakdown },
  };
};

test("named section: locked row format renders in both desktop and mobile regions", () => {
  const { detailRegions } = renderExpanded(withBreakdown(makeBreakdown()));

  expect(detailRegions).toHaveLength(2);
  detailRegions.forEach((region) => {
    expect(within(region).getByRole("heading", { name: "Instructors for this course" })).toBeVisible();
    expect(within(region).getByText(/^Source: USF InfoCenter grade reports/)).toBeVisible();

    const items = within(region).getAllByRole("listitem").filter((li) => li.textContent?.includes("grades"));
    expect(items[0]).toHaveTextContent("X. Ou");
    expect(within(items[0]).getByText(/^40% A/)).toBeVisible();
    expect(within(items[0]).getByText("175 grades")).toBeVisible();
    expect(within(items[0]).getByText("3 terms (Spr 25–Spr 26)")).toBeVisible();

    expect(within(region).getAllByText("This section")).toHaveLength(1);
    expect(within(region).getAllByRole("button", { name: CAVEAT })).toHaveLength(1);
  });
});

test("desktop and mobile instances render without duplicate id values", () => {
  renderExpanded(withBreakdown(makeBreakdown()));
  const ids = Array.from(document.body.querySelectorAll("[id]")).map((el) => el.id);
  expect(new Set(ids).size).toBe(ids.length);
  expect(document.getElementById("details-49100-instructors-heading")).not.toBeNull();
  expect(document.getElementById("mobile-details-49100-instructors-heading")).not.toBeNull();
});
