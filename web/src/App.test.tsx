import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";

import App from "./App";
import { syntheticRankings } from "./fixtures/rankings";
import type { RankingLoader, SectionRanking } from "./types/rankings";

const resolvedLoader: RankingLoader = async () => syntheticRankings;

const renderLoadedApp = async () => {
  const user = userEvent.setup();
  render(<App loader={resolvedLoader} mockMode />);
  const table = await screen.findByRole("table", { name: "Ranked USF course sections" });
  return { table, user };
};

const dataRows = (table: HTMLElement): HTMLElement[] =>
  within(table).getAllByRole("row").slice(1).filter((row) => !row.textContent?.includes("Policy signals"));

const rowForCrn = (table: HTMLElement, crn: string): HTMLElement => {
  const row = dataRows(table).find((candidate) => candidate.textContent?.includes(crn));
  if (!row) throw new Error(`Expected a row for CRN ${crn}.`);
  return row;
};

describe("course ranking page", () => {
  test("table renders rows", async () => {
    const { table } = await renderLoadedApp();
    expect(dataRows(table)).toHaveLength(7);
    expect(within(table).getByText("AMH 2020")).toBeInTheDocument();
  });

  test("filters by GenEd", async () => {
    const { table, user } = await renderLoadedApp();
    await user.selectOptions(screen.getByLabelText("GenEd"), "no");
    expect(rowForCrn(table, "17205")).toBeInTheDocument();
    expect(within(table).queryByText("19410")).not.toBeInTheDocument();
  });

  test("filters by modality", async () => {
    const { table, user } = await renderLoadedApp();
    await user.selectOptions(screen.getByLabelText("Modality"), "online");
    expect(within(table).getByText("AMH 2020")).toBeInTheDocument();
    expect(within(table).queryByText("BSC 1005")).not.toBeInTheDocument();
  });

  test("open seats toggle excludes full and unknown sections", async () => {
    const { table, user } = await renderLoadedApp();
    await user.click(screen.getByLabelText("Open seats only"));
    expect(within(table).queryByText("15502")).not.toBeInTheDocument();
    expect(within(table).queryByText("17205")).not.toBeInTheDocument();
  });

  test("sorts by easiness descending", async () => {
    const { table, user } = await renderLoadedApp();
    await user.selectOptions(screen.getByLabelText("Sort by"), "course");
    await user.selectOptions(screen.getByLabelText("Sort by"), "easiness");
    expect(dataRows(table)[0]).toHaveTextContent("AMH 2020");
    expect(dataRows(table)[0]).toHaveTextContent("9.1");
  });

  test("filters by confidence", async () => {
    const { table, user } = await renderLoadedApp();
    await user.selectOptions(screen.getByLabelText("Confidence"), "high");
    expect(dataRows(table)).toHaveLength(2);
    expect(within(table).getByText("BSC 1005")).toBeInTheDocument();
  });

  test("row details open from a keyboard-accessible button", async () => {
    const { table, user } = await renderLoadedApp();
    const button = within(rowForCrn(table, "19411")).getByRole("button");
    await user.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(within(table).getByRole("heading", { level: 3, name: "College Algebra" })).toBeInTheDocument();
    expect(within(table).getByText("Instructor + course history")).toBeInTheDocument();
  });

  test("historical syllabus signals are explicitly marked historical", async () => {
    const { table, user } = await renderLoadedApp();
    await user.click(within(rowForCrn(table, "14022")).getByRole("button"));
    expect(within(table).getAllByText("Historical reference").length).toBeGreaterThan(0);
    expect(within(table).getByText(/Historical syllabus reference · 202608/)).toBeInTheDocument();
  });

  test("unavailable signals render clearly", async () => {
    const { table } = await renderLoadedApp();
    expect(within(rowForCrn(table, "14023")).getByText("Unavailable")).toBeInTheDocument();
  });

  test("low-confidence state is labeled", async () => {
    const { table } = await renderLoadedApp();
    expect(within(rowForCrn(table, "16880")).getByText("Low confidence")).toBeInTheDocument();
  });

  test("API error state is announced", async () => {
    const errorLoader: RankingLoader = async () => {
      throw new Error("The API could not be reached.");
    };
    render(<App loader={errorLoader} mockMode={false} />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Rankings are unavailable");
    expect(alert).toHaveTextContent("The API could not be reached.");
  });

  test("loading state is announced", () => {
    const loadingLoader: RankingLoader = () => new Promise<SectionRanking[]>(() => undefined);
    render(<App loader={loadingLoader} mockMode={false} />);
    expect(screen.getByRole("status", { name: "Loading course rankings" })).toBeInTheDocument();
  });
});
