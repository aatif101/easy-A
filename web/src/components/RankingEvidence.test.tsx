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
