import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { section } from "./test/builders";
import type { RankingLoader, RankingQuery, SectionLoader, SectionRanking } from "./types/rankings";

const terms = async () => [
  { term: "202601", term_name: "Spring 2026", year: 2026, season: "Spring" },
  { term: "202701", term_name: "Spring 2027", year: 2027, season: "Spring" },
];
const syncStatus = vi.fn();

const encSections: SectionRanking[] = [
  section("11111", "Low Grader", 0.42),
  section("22222", "High Grader", 0.88),
  section("33333", null, null),
  section("44444", "Few Grades", 0.97, { gradeCount: 9 }),
];

const loaderFor = (items: SectionRanking[]): RankingLoader =>
  vi.fn(async (query: RankingQuery) => {
    const matching = items.filter(
      (item) =>
        (!query.subject || item.subject === query.subject) &&
        (!query.course_number || item.course_number === query.course_number) &&
        (!query.gened_code || item.gened_attributes.some(({ code }) => code === query.gened_code)),
    );
    return { items: matching.slice(query.offset, query.offset + query.limit), total: matching.length, limit: query.limit, offset: query.offset };
  });

const renderApp = (url: string, rankingLoader = loaderFor(encSections), sectionLoader: SectionLoader = vi.fn(async () => null)) => {
  window.history.replaceState(null, "", url);
  return render(
    <App rankingLoader={rankingLoader} sectionLoader={sectionLoader} termsLoader={terms} syncStatusLoader={syncStatus} mockMode={false} />,
  );
};

beforeEach(() => {
  syncStatus.mockRejectedValue(new Error("offline"));
});

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("header brand", () => {
  it.each(["/", "/?q=ENC%201101"])("shows the standalone Bull beside the existing name at %s", (url) => {
    renderApp(url);
    const home = within(screen.getByRole("banner")).getByRole("link", { name: "Easy-A home" });
    const logo = within(home).getByRole("img", { name: "USF Bull logo" });
    expect(logo).toHaveAttribute("src", expect.stringContaining("usf-bull.svg"));
    expect(logo).toHaveAttribute("width", "56");
    expect(logo).toHaveAttribute("height", "56");
    expect(logo.nextElementSibling).toHaveTextContent(/^easyA$/);
    expect(home).toHaveTextContent(/^easyA$/);
    expect(home).not.toHaveTextContent(/USF|University of South Florida/i);
  });

  it("keeps the brand as one keyboard-accessible home link", async () => {
    const user = userEvent.setup();
    renderApp("/?q=ENC%201101");
    const home = screen.getByRole("link", { name: "Easy-A home" });
    await user.tab();
    expect(home).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(await screen.findByRole("heading", { name: "Who gives the most A's?" })).toBeInTheDocument();
  });
});

describe("course search", () => {
  it("lists every section with the most A's first and missing history last", async () => {
    renderApp("/?q=ENC%201101");
    expect(await screen.findByRole("heading", { name: /ENC 1101/ })).toBeInTheDocument();
    const table = screen.getByRole("table");
    const crns = within(table)
      .getAllByRole("row")
      .slice(1)
      .map((row) => row.querySelector("td")?.textContent?.match(/\d{5}/)?.[0]);
    expect(crns).toEqual(["22222", "11111", "44444", "33333"]);
    expect(within(table).getByText("88%")).toBeInTheDocument();
    expect(within(table).getByText("9 grades · too few to trust")).toBeInTheDocument();
    expect(within(table).getByText("Instructor not announced yet")).toBeInTheDocument();
  });

  it("filters to sections whose instructor has grade history", async () => {
    renderApp("/?q=ENC%201101");
    await screen.findByRole("table");
    await userEvent.click(screen.getByRole("button", { name: "Has grade history" }));
    expect(screen.getByRole("status")).toHaveTextContent("Showing 3 of 4 sections");
  });

  it("copies a CRN for OASIS", async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText");
    renderApp("/?q=ENC%201101");
    const table = await screen.findByRole("table");
    await user.click(within(table).getByRole("button", { name: "Copy CRN 22222" }));
    expect(writeText).toHaveBeenCalledWith("22222");
    expect(await within(table).findByRole("button", { name: "Copied: CRN 22222" })).toBeInTheDocument();
  });

  it("explains an unknown course instead of showing an empty table", async () => {
    renderApp("/?q=ENC%209999");
    expect(await screen.findByText("No Spring 2027 sections of ENC 9999")).toBeInTheDocument();
  });

  it("explains searches it cannot read", async () => {
    renderApp("/?q=psychology");
    expect(await screen.findByText('Nothing matches "psychology"')).toBeInTheDocument();
  });
});

describe("CRN search", () => {
  it("shows the section and links to the whole course", async () => {
    const sectionLoader: SectionLoader = vi.fn(async (_term, crn) => (crn === "22222" ? encSections[1] : null));
    renderApp("/?q=22222", loaderFor(encSections), sectionLoader);
    expect(await screen.findByRole("heading", { name: "CRN 22222" })).toBeInTheDocument();
    expect(sectionLoader).toHaveBeenCalledWith("202701", "22222", expect.anything());
    expect(screen.getByRole("link", { name: "Compare every ENC 1101 section" })).toHaveAttribute("href", "?q=ENC%201101");
  });
});

describe("home", () => {
  it("ranks Gen Ed sections by the instructor's A share and groups repeat sections", async () => {
    const social = [
      section("50001", "Same Person", 0.91, { subject: "AMH", course_number: "2010", gened_attributes: [{ code: "SGES", label: "x" }] }),
      section("50002", "Same Person", 0.91, { subject: "AMH", course_number: "2010", gened_attributes: [{ code: "UGES", label: "y" }] }),
      section("50003", "Other Person", 0.6, { subject: "PSY", course_number: "2012", gened_attributes: [{ code: "SGES", label: "x" }] }),
      section("50004", null, null, { subject: "PSY", course_number: "2012", gened_attributes: [{ code: "SGES", label: "x" }] }),
    ];
    renderApp("/", loaderFor(social));
    expect(await screen.findByRole("heading", { name: "Social Sciences sections with high A rates" })).toBeInTheDocument();
    const items = await screen.findAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("91%");
    expect(items[0]).toHaveTextContent("50001");
    expect(items[0]).toHaveTextContent("50002");
    expect(items[1]).toHaveTextContent("60%");
  });

  it("searches from the landing page", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.type(await screen.findByRole("searchbox"), "enc 1101{Enter}");
    expect(await screen.findByRole("heading", { name: /ENC 1101/ })).toBeInTheDocument();
    expect(window.location.search).toBe("?q=enc%201101");
  });
});
