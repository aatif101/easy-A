import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import App from "./App";
import { syntheticRankings } from "./fixtures/rankings";
import type {
  MetadataLoader,
  RankingLoader,
  RankingMetadata,
  RankingQuery,
  RankingsSearchResponse,
} from "./types/rankings";

const metadata: RankingMetadata = {
  terms: [
    { term: "202801", term_name: "Spring 2028", year: 2028, season: "Spring" },
    { term: "202701", term_name: "Spring 2027", year: 2027, season: "Spring" },
    { term: "202608", term_name: "Fall 2026", year: 2026, season: "Fall" },
  ],
  subjects: [{ subject: "AMH" }, { subject: "BSC" }, { subject: "ENC" }, { subject: "MAC" }, { subject: "PSY" }],
  genedAttributes: [
    { code: "COMM", label: "Communication" },
    { code: "SMEL", label: "Enhanced General Education Mathematics" },
  ],
  deliveryMethods: [
    { code: "AD", label: "All Online 100%" },
    { code: "CL", label: "Classroom 1–49%" },
    { code: "HB", label: "Hybrid Blend 50–79%" },
  ],
};

const resolvedMetadataLoader: MetadataLoader = async () => metadata;

const pageFor = (
  query: RankingQuery,
  items = syntheticRankings,
  total = items.length,
): RankingsSearchResponse => ({ items, total, limit: query.limit, offset: query.offset });

const resolvedRankingLoader: RankingLoader = async (query) => pageFor(query);

const renderLoadedApp = async (
  rankingLoader: RankingLoader = resolvedRankingLoader,
  metadataLoader: MetadataLoader = resolvedMetadataLoader,
) => {
  const user = userEvent.setup();
  render(<App rankingLoader={rankingLoader} metadataLoader={metadataLoader} mockMode={false} />);
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
  test("prefers beta term 202701 from metadata", async () => {
    await renderLoadedApp();
    expect(screen.getByLabelText("Term")).toHaveValue("202701");
    expect(screen.getByRole("heading", { name: "Spring 2027 course index" })).toBeInTheDocument();
  });

  test("uses the most recent metadata term when 202701 is absent", async () => {
    const alternateMetadata: MetadataLoader = async () => ({
      ...metadata,
      terms: [metadata.terms[2], metadata.terms[0]],
    });
    await renderLoadedApp(resolvedRankingLoader, alternateMetadata);
    expect(screen.getByLabelText("Term")).toHaveValue("202801");
  });

  test("sends selected filters through the ranking loader", async () => {
    const loader = vi.fn<RankingLoader>(async (query) => pageFor(query));
    const { user } = await renderLoadedApp(loader);

    await user.type(screen.getByRole("searchbox", { name: /Course code/ }), "MAC 1105");
    await user.selectOptions(screen.getByLabelText("GenEd"), "SMEL");
    await user.selectOptions(screen.getByLabelText("Modality"), "HB");
    await user.click(screen.getByLabelText("Open seats only"));
    await user.selectOptions(screen.getByLabelText("Confidence"), "medium");
    await user.selectOptions(screen.getByLabelText("Sort by"), "course");
    fireEvent.change(screen.getByRole("slider", { name: /Minimum easiness/ }), { target: { value: "7.5" } });

    await waitFor(() => expect(loader).toHaveBeenLastCalledWith(
      expect.objectContaining({
        term: "202701",
        subject: "MAC",
        course_number: "1105",
        gened_code: "SMEL",
        delivery_method: "HB",
        seats_open: true,
        min_easiness: 7.5,
        confidence: "medium",
        sort: "course",
        limit: 50,
        offset: 0,
      }),
      expect.any(AbortSignal),
    ));
  });

  test("pagination uses offset and a filter change resets it", async () => {
    const loader = vi.fn<RankingLoader>(async (query) => pageFor(query, syntheticRankings, 143));
    const { user } = await renderLoadedApp(loader);

    await user.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(loader).toHaveBeenLastCalledWith(
      expect.objectContaining({ limit: 50, offset: 50 }),
      expect.any(AbortSignal),
    ));
    await user.selectOptions(screen.getByLabelText("Subject"), "MAC");
    await waitFor(() => expect(loader).toHaveBeenLastCalledWith(
      expect.objectContaining({ subject: "MAC", limit: 50, offset: 0 }),
      expect.any(AbortSignal),
    ));
  });

  test("renders the API total", async () => {
    await renderLoadedApp(async (query) => pageFor(query, syntheticRankings, 143));
    expect(screen.getAllByText("Showing 1–7 of 143 sections")).toHaveLength(2);
  });

  test("renders an empty result state", async () => {
    const user = userEvent.setup();
    render(<App rankingLoader={async (query) => pageFor(query, [], 0)} metadataLoader={resolvedMetadataLoader} />);
    await user.type(await screen.findByRole("searchbox", { name: /Course code/ }), "ENC 1101");
    expect(await screen.findByRole("heading", { name: "No sections match these filters" })).toBeInTheDocument();
  });

  test("announces an API failure", async () => {
    const errorLoader: RankingLoader = async () => {
      throw new Error("The API could not be reached.");
    };
    render(<App rankingLoader={errorLoader} metadataLoader={resolvedMetadataLoader} mockMode={false} />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Rankings are unavailable");
    expect(alert).toHaveTextContent("The API could not be reached.");
  });

  test("renders unknown seats safely", async () => {
    const { table } = await renderLoadedApp();
    expect(within(rowForCrn(table, "17205")).getByText("Unknown")).toBeInTheDocument();
  });

  test("renders a blank current instructor assignment as Staff", async () => {
    const staffRanking = {
      ...syntheticRankings[0],
      instructor: null,
      instructor_provenance: {
        ...syntheticRankings[0].instructor_provenance,
        freshness: "unavailable" as const,
        detail: "latest instructor observation is blank",
      },
    };
    const { table } = await renderLoadedApp(async (query) => pageFor(query, [staffRanking]));
    expect(within(rowForCrn(table, staffRanking.crn)).getByText("Staff")).toBeInTheDocument();
  });

  test("warns that historical syllabus policy may have changed", async () => {
    const { table, user } = await renderLoadedApp();
    await user.click(within(rowForCrn(table, "14022")).getByRole("button"));
    expect(within(table).getByText(/Historical syllabus reference · 202608/)).toBeInTheDocument();
    expect(within(table).getByText("This policy comes from a prior term and may have changed.")).toBeInTheDocument();
  });

  test("renders low confidence with its limited-data explanation", async () => {
    const { table } = await renderLoadedApp();
    const row = rowForCrn(table, "16880");
    expect(within(row).getByText("Low confidence")).toBeInTheDocument();
    expect(within(row).getByRole("button", { name: "Based on limited historical data." })).toBeInTheDocument();
  });

  test("renders GenEd code and readable label", async () => {
    const { table } = await renderLoadedApp();
    const row = rowForCrn(table, "19410");
    expect(within(row).getByText("SMEL")).toBeInTheDocument();
    expect(within(row).getByText(/Enhanced General Education Mathematics/)).toBeInTheDocument();
  });

  test("announces term metadata failure without requesting rankings", async () => {
    const rankingLoader = vi.fn<RankingLoader>();
    const metadataLoader: MetadataLoader = async () => {
      throw new Error("Terms endpoint unavailable.");
    };
    render(<App rankingLoader={rankingLoader} metadataLoader={metadataLoader} mockMode={false} />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Metadata unavailable");
    expect(alert).toHaveTextContent("Terms endpoint unavailable.");
    expect(rankingLoader).not.toHaveBeenCalled();
  });
});
