import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
  test("uses the newest term from metadata", async () => {
    await renderLoadedApp();
    expect(screen.getByLabelText("Term")).toHaveValue("202801");
    expect(screen.getByRole("heading", { name: "Spring 2028 course index" })).toBeInTheDocument();
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
        term: "202801",
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
    expect(await screen.findByRole("heading", { name: "No sections are currently available for this search" })).toBeInTheDocument();
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


const largeItems = Array.from({ length: 500 }, (_, index) => ({
  ...syntheticRankings[index % syntheticRankings.length],
  crn: String(30000 + index),
  course_title: `Advanced interdisciplinary course ${index} with extensive applied research and laboratory practice`,
  instructor: `Professor Alexandra Maria Long-Instructor-Name ${index}`,
  gened_attributes: Array.from({ length: 8 }, (_, attribute) => ({ code: `G${attribute}`, label: `Extended interdisciplinary attribute ${attribute}` })),
}));
const pagedLoader = (total: number) => vi.fn<RankingLoader>(async (query) =>
  pageFor(query, largeItems.slice(query.offset, Math.min(total, query.offset + query.limit)), total));

test.each([0, 5, 50, 51, 143, 500])("server pagination for total %s", async (total) => {
  const loader = pagedLoader(total);
  const user = userEvent.setup();
  render(<App rankingLoader={loader} metadataLoader={resolvedMetadataLoader} mockMode={false} />);
  await waitFor(() => expect(screen.getAllByText(`Showing ${total ? 1 : 0}–${Math.min(50, total)} of ${total} sections`).length).toBeGreaterThan(0));
  expect(screen.getByRole("button", { name: "Previous" })).toHaveAttribute("aria-disabled", "true");
  if (total <= 50) expect(screen.getByRole("button", { name: "Next" })).toHaveAttribute("aria-disabled", "true");
  for (let offset = 50; offset < total; offset += 50) {
    await user.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(screen.getAllByText(`Showing ${offset + 1}–${Math.min(offset + 50, total)} of ${total} sections`).length).toBeGreaterThan(0));
    expect(loader).toHaveBeenLastCalledWith(expect.objectContaining({ offset, limit: 50 }), expect.any(AbortSignal));
    expect(dataRows(screen.getByRole("table"))).toHaveLength(Math.min(50, total - offset));
  }
  expect(screen.getByRole("button", { name: "Next" })).toHaveAttribute("aria-disabled", "true");
  if (total > 50) {
    await user.click(screen.getByRole("button", { name: "Previous" }));
    await waitFor(() => expect(loader).toHaveBeenLastCalledWith(expect.objectContaining({ offset: Math.floor((total - 1) / 50) * 50 - 50 }), expect.any(AbortSignal)));
  }
}, 20000);

test("term change resets an advanced page", async () => {
  const loader = pagedLoader(143);
  const { user } = await renderLoadedApp(loader);
  await user.click(screen.getByRole("button", { name: "Next" }));
  await screen.findAllByText("Showing 51–100 of 143 sections");
  await user.selectOptions(screen.getByLabelText("Term"), "202608");
  await waitFor(() => expect(loader).toHaveBeenLastCalledWith(expect.objectContaining({ term: "202608", offset: 0 }), expect.any(AbortSignal)));
});

test("many API subjects and arbitrary exact course codes", async () => {
  const loader = pagedLoader(143);
  const subjects = Array.from({ length: 150 }, (_, i) => ({ subject: `S${i}` }));
  const { user } = await renderLoadedApp(loader, async () => ({ ...metadata, subjects: [...subjects, { subject: "CHM" }] }));
  expect(within(screen.getByLabelText("Subject")).getAllByRole("option")).toHaveLength(152);
  await user.selectOptions(screen.getByLabelText("Subject"), "S149");
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "CHM 2045L" } });
  await waitFor(() => expect(loader).toHaveBeenLastCalledWith(expect.objectContaining({ subject: "CHM", course_number: "2045L", limit: 50 }), expect.any(AbortSignal)));
  const table = await screen.findByRole("table");
  expect(within(table).getByText(largeItems[0].course_title)).toBeInTheDocument();
  expect(within(table).getByText(largeItems[0].instructor)).toBeInTheDocument();
  expect(within(table).getAllByText(/Extended interdisciplinary attribute 7/)).toHaveLength(50);
});

test("recovers an empty page when data shrinks", async () => {
  const loader = vi.fn<RankingLoader>(async (query) => query.offset > 0 ? pageFor(query, [], 5) : pageFor(query, largeItems.slice(0, 5), 51));
  const { user } = await renderLoadedApp(loader);
  await user.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() => expect(loader).toHaveBeenCalledTimes(3));
  expect(loader).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 0 }), expect.any(AbortSignal));
  await screen.findByRole("table");
});

test("late responses cannot replace a newer search, even if abort is ignored", async () => {
  let finishOld!: (page: RankingsSearchResponse) => void;
  const loader = vi.fn<RankingLoader>().mockImplementationOnce(() => new Promise((resolve) => { finishOld = resolve; })).mockImplementation(async (query) => pageFor(query, [largeItems[1]]));
  render(<App rankingLoader={loader} metadataLoader={resolvedMetadataLoader} />);
  await waitFor(() => expect(loader).toHaveBeenCalledOnce());
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "CHM2045L" } });
  await screen.findByRole("table");
  await act(async () => finishOld({ items: [largeItems[0]], total: 1, offset: 0, limit: 50 }));
  expect(screen.queryByText(largeItems[0].course_title)).not.toBeInTheDocument();
  expect(screen.getAllByText(largeItems[1].course_title)).toHaveLength(2);
});

test("old rows disappear while a changed query is pending", async () => {
  const loader = vi.fn<RankingLoader>().mockImplementationOnce(async (query) => pageFor(query)).mockImplementation(() => new Promise(() => {}));
  await renderLoadedApp(loader);
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "CHM2045L" } });
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
  expect(screen.getByRole("status", { name: "Loading course rankings" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Next" })).toHaveAttribute("aria-disabled", "true");
});


test("pagination keeps keyboard focus and blocks duplicate pending requests", async () => {
  let finish!: (page: RankingsSearchResponse) => void;
  const loader = vi.fn<RankingLoader>().mockImplementationOnce(async (query) => pageFor(query, largeItems.slice(0, 50), 143)).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  const { user } = await renderLoadedApp(loader);
  const next = screen.getByRole("button", { name: "Next" });
  next.focus();
  await user.keyboard("{Enter}");
  expect(next).toHaveFocus();
  expect(next).toHaveAttribute("aria-disabled", "true");
  await user.keyboard("{Enter}");
  expect(loader).toHaveBeenCalledTimes(2);
  await act(async () => finish({ items: largeItems.slice(50, 100), total: 143, offset: 50, limit: 50 }));
  expect(next).toHaveFocus();
  expect(next).toHaveAttribute("aria-disabled", "false");
});

test("an unfiltered empty term has its own state", async () => {
  render(<App rankingLoader={pagedLoader(0)} metadataLoader={resolvedMetadataLoader} />);
  expect(await screen.findByRole("heading", { name: "No sections available for Spring 2028" })).toBeInTheDocument();
  expect(screen.getByText("This term is listed by the API but has no searchable section data.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Reset filters" })).not.toBeInTheDocument();
});
