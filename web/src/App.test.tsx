import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { parseSearch } from "./lib/search";
import { section } from "./test/builders";
import type { RankingLoader, RankingQuery, SectionLoader, SectionRanking } from "./types/rankings";

const terms = async () => [
  { term: "202601", term_name: "Spring 2026", year: 2026, season: "Spring" },
  { term: "202701", term_name: "Spring 2027", year: 2027, season: "Spring" },
];
const syncStatus = vi.fn();
const discoveryLoader = vi.fn(async (_term: string, q: string) => {
  const parsed = parseSearch(q);
  return { as_of: "2026-10-07T12:00:00Z", kind: parsed.kind, subject: parsed.kind === "subject" || parsed.kind === "course" ? parsed.subject : "", course_number: parsed.kind === "course" ? parsed.courseNumber : "", crn: parsed.kind === "crn" ? parsed.crn : null, courses: [], instructors: [], course_total: 0, instructor_total: 0, limit: 20, offset: 0, identity_note: "Separate course identities" };
});

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
    <App rankingLoader={rankingLoader} sectionLoader={sectionLoader} termsLoader={terms} syncStatusLoader={syncStatus} discoveryLoader={discoveryLoader} mockMode={false} />,
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
    expect(await screen.findByRole("heading", { name: "See the grades before you register." })).toBeInTheDocument();
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

describe("search routing", () => {
  beforeEach(() => {
    discoveryLoader.mockClear();
  });

  it.each(["/?q=ENC%201101", "/?q=ENC", "/?q=22222"])(
    "loads sections for %s without waiting on discovery", async (url) => {
      renderApp(url, loaderFor(encSections), async () => encSections[1]);
      expect(await screen.findByRole("table")).toBeInTheDocument();
      expect(discoveryLoader).not.toHaveBeenCalled();
    },
  );

  it.each([["/?q=calculus%201", "calculus 1"], ["/?q=1101", "1101"], ["/?q=LEE", "LEE"]])(
    "sends title, number and non-subject searches to discovery: %s", async (url, q) => {
      renderApp(url, loaderFor(encSections));
      expect(await screen.findByText(`Nothing matches "${q}"`)).toBeInTheDocument();
      expect(discoveryLoader).toHaveBeenCalledWith("202701", q, 0, expect.anything());
    },
  );
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
  it("loads no rankings until the student picks a door", async () => {
    const rankingLoader = loaderFor(encSections);
    renderApp("/", rankingLoader);
    expect(await screen.findByRole("heading", { name: "I just need a GenEd" })).toBeInTheDocument();
    expect(rankingLoader).not.toHaveBeenCalled();
  });

  it("opens a Gen Ed area from its door", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.click(await screen.findByRole("link", { name: "Communication" }));
    expect(await screen.findByRole("heading", { name: "Communication", level: 1 })).toBeInTheDocument();
    expect(window.location.search).toBe("?gened=communication");
  });

  it("searches from the landing page", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.type(await screen.findByRole("searchbox"), "enc 1101{Enter}");
    expect(await screen.findByRole("heading", { name: /ENC 1101/ })).toBeInTheDocument();
    expect(window.location.search).toBe("?q=enc%201101");
  });
});

describe("RMP search links across results pages", () => {
  it.each(["/?q=ENC%201101", "/?q=ENC", "/?q=22222", "/?gened=communication"])(
    "links the named professor in both section layouts at %s", async (url) => {
      renderApp(url, loaderFor(encSections), async () => encSections[1]);
      const table = await screen.findByRole("table");
      const links = screen.getAllByRole("link", { name: "Search for High Grader on Rate My Professors" });
      expect(links).toHaveLength(2);
      expect(within(table).getByRole("link", { name: "Search for High Grader on Rate My Professors" })).toBeInTheDocument();
      for (const link of links) {
        expect(link).toHaveAttribute("href", "https://www.ratemyprofessors.com/search/professors/1262?q=High%20Grader");
      }
    },
  );
});

describe("score guide", () => {
  it("opens from the landing page and explains each part of a row", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.click(await screen.findByRole("link", { name: "How to read the score" }));
    expect(await screen.findByRole("heading", { name: "How to read the score", level: 1 })).toBeInTheDocument();
    expect(window.location.search).toBe("?guide");
    for (const name of ["The score (A%)", "The grade bar", "Grades and terms", "When there is no score", "RMP", "Copy CRN"]) {
      expect(screen.getByRole("heading", { name, level: 2 })).toBeInTheDocument();
    }
  });

  it("is linked from results pages", async () => {
    renderApp("/?q=ENC%201101");
    await screen.findByRole("table");
    expect(screen.getByRole("link", { name: "How to read the score" })).toHaveAttribute("href", "?guide");
  });

  it("loads directly from its URL", async () => {
    renderApp("/?guide");
    expect(await screen.findByRole("heading", { name: "How to read the score", level: 1 })).toBeInTheDocument();
  });
});
