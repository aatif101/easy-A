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

const eachRegion = (regions: HTMLElement[], assert: (region: HTMLElement) => void) => {
  expect(regions).toHaveLength(2);
  regions.forEach(assert);
};

const HEADING_NAMED = "Instructors for this course";
const HEADING_STAFF = "Historically taught by";
const USED_IN_SCORE = "Used in this section's score";

const manyRows = (count: number): InstructorHistoryRow[] => [
  row({ name: "X. Ou", a_share: 0.4, effective_n: 175, easiness_score: 6.1, is_current: true }),
  ...Array.from({ length: count - 1 }, (_, index) =>
    row({ name: `Synthetic Instructor ${index + 1}`, effective_n: 300 - index * 10 }),
  ),
];

test("Staff section: historical heading and explainer, no pinned row, no score claim (D-11)", () => {
  const breakdown = makeBreakdown({
    instructors: [
      row({ name: "J. Ligatti", effective_n: 203, a_share: 0.251 }),
      row({ name: "A. Example", effective_n: 120, a_share: 0.5, term_count: 1, first_term: "202508", last_term: "202508" }),
    ],
    current_instructor: null,
    current_instructor_has_history: false,
  });
  // A hostile payload that flags a row current must still not pin or highlight it.
  breakdown.instructors[0].is_current = true;
  const { detailRegions } = renderExpanded(withBreakdown(breakdown, { instructor: null }));

  eachRegion(detailRegions, (region) => {
    expect(within(region).getByRole("heading", { name: HEADING_STAFF })).toBeVisible();
    expect(within(region).queryByRole("heading", { name: HEADING_NAMED })).not.toBeInTheDocument();
    expect(
      within(region).getByText(
        "This section's instructor is not yet named. These instructors taught this course in past terms. They do not affect this section's score.",
      ),
    ).toBeVisible();
    expect(within(region).queryAllByText("This section")).toHaveLength(0);
    expect(within(region).queryAllByText(USED_IN_SCORE)).toHaveLength(0);
    expect(region.querySelector(".border-l-spruce")).toBeNull();
    expect(within(region).getByText("J. Ligatti")).toBeVisible();
    expect(within(region).getAllByRole("button", { name: CAVEAT })).toHaveLength(1);
  });
});

test("Staff section with no qualifying instructors shows the dashed empty note", () => {
  const breakdown = makeBreakdown({
    status: "no_instructor_history",
    instructors: [],
    current_instructor: null,
    current_instructor_has_history: false,
  });
  const { detailRegions } = renderExpanded(withBreakdown(breakdown, { instructor: null }));
  eachRegion(detailRegions, (region) => {
    expect(
      within(region).getByText(
        "No instructor-level grade history is recorded for this course. Course-wide history above still applies.",
      ),
    ).toBeVisible();
    expect(within(region).queryByText(/% A/)).not.toBeInTheDocument();
  });
});

test("lab section: only the dashed note, no heading, no tip, no rows (D-13)", () => {
  const breakdown = makeBreakdown({ status: "lab_section", instructors: [], current_instructor: null });
  const { detailRegions } = renderExpanded(withBreakdown(breakdown));
  eachRegion(detailRegions, (region) => {
    expect(
      within(region).getByText("Instructor history is not shown for lab sections. The figures above are course-wide."),
    ).toBeVisible();
    expect(within(region).queryByRole("heading", { name: HEADING_NAMED })).not.toBeInTheDocument();
    expect(within(region).queryByRole("heading", { name: HEADING_STAFF })).not.toBeInTheDocument();
    expect(within(region).queryAllByRole("button", { name: CAVEAT })).toHaveLength(0);
    expect(within(region).queryByText(/% A/)).not.toBeInTheDocument();
    // Course-wide figures are untouched.
    expect(within(region).getByText("Course-level history")).toBeVisible();
  });
});

test("non-course-history scopes render no block even when a breakdown object is present (D-20)", () => {
  const breakdown = makeBreakdown();
  const scopes: Partial<SectionRanking>[] = [
    { crn: "49101", score_source: "subject", effective_n: 45 }, // subject_fallback
    { crn: "49102", score_source: "global", effective_n: 22 }, // no_course_evidence
    { crn: "49103", score_source: "course", effective_n: 0 }, // no_letter_grade_history
  ];
  for (const scope of scopes) {
    const { detailRegions } = renderExpanded(withBreakdown(breakdown, scope));
    eachRegion(detailRegions, (region) => {
      expect(within(region).queryByRole("heading", { name: HEADING_NAMED })).not.toBeInTheDocument();
      expect(within(region).queryByRole("heading", { name: HEADING_STAFF })).not.toBeInTheDocument();
      expect(within(region).queryByText(/^Source: USF InfoCenter/)).not.toBeInTheDocument();
      expect(within(region).queryAllByRole("button", { name: CAVEAT })).toHaveLength(0);
    });
    document.body.innerHTML = "";
  }
});

test("course_history with a null or absent breakdown renders no block", () => {
  for (const [crn, breakdown] of [["49104", null], ["49105", undefined]] as const) {
    const ranking = withBreakdown(null, { crn });
    if (breakdown === undefined) delete ranking.historical_analytics.instructor_breakdown;
    const { detailRegions } = renderExpanded(ranking);
    eachRegion(detailRegions, (region) => {
      expect(within(region).queryByRole("heading", { name: HEADING_NAMED })).not.toBeInTheDocument();
      expect(within(region).queryByRole("heading", { name: HEADING_STAFF })).not.toBeInTheDocument();
    });
    document.body.innerHTML = "";
  }
});

test("pinned instructor is first exactly once; under-cutoff instructors only appear in the Others line", () => {
  const breakdown = makeBreakdown({
    instructors: [
      row({ name: "J. Ligatti", effective_n: 203 }),
      row({ name: "X. Ou", a_share: 0.4, effective_n: 175, easiness_score: 6.1, is_current: true }),
    ],
    other_instructor_count: 3,
    collapse_min_effective_n: 12,
  });
  const { detailRegions } = renderExpanded(withBreakdown(breakdown));
  eachRegion(detailRegions, (region) => {
    const list = within(region).getAllByRole("list").find((ul) => ul.textContent?.includes("X. Ou"));
    expect(list).toBeDefined();
    const items = within(list as HTMLElement).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("X. Ou");
    expect(within(region).getAllByText("X. Ou")).toHaveLength(1);
    expect(within(region).getAllByText("This section")).toHaveLength(1);
    expect(within(region).getByText("3 other instructors with under 12 grades each")).toBeVisible();
    expect(region.querySelectorAll("details")).toHaveLength(0);
  });
});

test("Others line uses the singular form for one instructor", () => {
  const { detailRegions } = renderExpanded(
    withBreakdown(makeBreakdown({ other_instructor_count: 1, collapse_min_effective_n: 12 })),
  );
  eachRegion(detailRegions, (region) => {
    expect(within(region).getByText("1 other instructor with under 12 grades")).toBeVisible();
  });
});

test("a one-instructor course renders its row with no disclosure and no Others line", () => {
  const breakdown = makeBreakdown({
    instructors: [row({ name: "X. Ou", effective_n: 1, term_count: 1, first_term: "202508", last_term: "202508", is_current: true })],
  });
  const { detailRegions } = renderExpanded(withBreakdown(breakdown));
  eachRegion(detailRegions, (region) => {
    expect(within(region).getByText("1 grade")).toBeVisible();
    expect(within(region).getByText("1 term (Fall 25)")).toBeVisible();
    expect(region.querySelectorAll("details")).toHaveLength(0);
    expect(within(region).queryByText(/other instructor/)).not.toBeInTheDocument();
  });
});

test("at most 5 rows are visible; the rest sit in a native disclosure with the total count", () => {
  const breakdown = makeBreakdown({ instructors: manyRows(7) });
  const { detailRegions } = renderExpanded(withBreakdown(breakdown));
  eachRegion(detailRegions, (region) => {
    const details = region.querySelector("details");
    expect(details).not.toBeNull();
    expect(within(details as HTMLElement).getByText("Show all 7 instructors")).toBeInTheDocument();
    expect(within(details as HTMLElement).getAllByRole("listitem", { hidden: true })).toHaveLength(2);
    // Pinned row stays first and is not repeated inside the disclosure.
    expect(within(region).getAllByText("X. Ou")).toHaveLength(1);
    const visible = within(region).getAllByRole("listitem").filter((li) => li.textContent?.includes("% A") && !li.closest("details"));
    expect(visible).toHaveLength(5);
  });
});

test("below the scoring minimum: Not scored over the API's minimum, Limited sample chip", () => {
  const breakdown = makeBreakdown({
    scoring_min_effective_n: 25,
    instructors: [
      row({ name: "X. Ou", is_current: true }),
      row({ name: "L. Small", effective_n: 20, easiness_score: null, scored: false }),
    ],
  });
  const { detailRegions } = renderExpanded(withBreakdown(breakdown));
  eachRegion(detailRegions, (region) => {
    expect(within(region).getByText("Not scored")).toBeVisible();
    expect(within(region).getByText("Under 25 grades")).toBeVisible();
    expect(within(region).queryByText("Under 30 grades")).not.toBeInTheDocument();
    expect(within(region).getAllByText("Limited sample")).toHaveLength(1);
  });
});

test("Based on 1 term appears on the one-term row only", () => {
  const breakdown = makeBreakdown({
    instructors: [
      row({ name: "X. Ou", is_current: true }),
      row({ name: "N. Newcomer", term_count: 1, first_term: "202601", last_term: "202601" }),
    ],
  });
  const { detailRegions } = renderExpanded(withBreakdown(breakdown));
  eachRegion(detailRegions, (region) => {
    const chips = within(region).getAllByText("Based on 1 term");
    expect(chips).toHaveLength(1);
    expect(chips[0].closest("li")).toHaveTextContent("N. Newcomer");
    expect(within(region).getByText("1 term (Spr 26)")).toBeVisible();
  });
});

test("Used in this section's score shows for an instructor_course ranking and not for a course-scored one", () => {
  const { detailRegions } = renderExpanded(
    withBreakdown(makeBreakdown(), { crn: "49110", score_source: "instructor_course" }),
  );
  eachRegion(detailRegions, (region) => {
    expect(within(region).getAllByText(USED_IN_SCORE)).toHaveLength(1);
  });
  document.body.innerHTML = "";

  const course = renderExpanded(withBreakdown(makeBreakdown(), { crn: "49111", score_source: "course" }));
  eachRegion(course.detailRegions, (region) => {
    expect(within(region).queryAllByText(USED_IN_SCORE)).toHaveLength(0);
  });
});

test("pinned current instructor with no history: explanatory row, never repeated", () => {
  const breakdown = makeBreakdown({
    instructors: [row({ name: "J. Ligatti", effective_n: 203 })],
    current_instructor: "X. Ou",
    current_instructor_has_history: false,
  });
  const { detailRegions } = renderExpanded(withBreakdown(breakdown));
  eachRegion(detailRegions, (region) => {
    expect(within(region).getAllByText("X. Ou")).toHaveLength(1);
    expect(within(region).getByText("No recorded grade history for this instructor in this course.")).toBeVisible();
    expect(within(region).getByText("This section's score uses course-wide history.")).toBeVisible();
    expect(within(region).getAllByText("This section")).toHaveLength(1);
    expect(within(region).queryAllByText(USED_IN_SCORE)).toHaveLength(0);
    const items = within(region).getAllByRole("listitem").filter((li) => li.textContent?.includes("X. Ou"));
    expect(items[0]).toBe(within(region).getAllByRole("listitem").find((li) => li.textContent?.includes("X. Ou")));
  });
});

test("pinned unscored row says it is not used and the score uses course-wide history", () => {
  const breakdown = makeBreakdown({
    instructors: [row({ name: "X. Ou", effective_n: 18, easiness_score: null, scored: false, is_current: true })],
  });
  const { detailRegions } = renderExpanded(withBreakdown(breakdown, { score_source: "instructor_course" }));
  eachRegion(detailRegions, (region) => {
    expect(
      within(region).getByText("Not used in this section's score. This section's score uses course-wide history."),
    ).toBeVisible();
    expect(within(region).queryAllByText(USED_IN_SCORE)).toHaveLength(0);
  });
});

test("ids stay unique with the disclosure and Staff variants present", () => {
  renderExpanded(withBreakdown(makeBreakdown({ instructors: manyRows(8) })));
  const ids = Array.from(document.body.querySelectorAll("[id]")).map((el) => el.id);
  expect(new Set(ids).size).toBe(ids.length);
});
