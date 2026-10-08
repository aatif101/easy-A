import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HomePage } from "./HomePage";
import { section } from "../test/builders";
import type { RankingQuery, SectionRanking } from "../types/rankings";

const sections: SectionRanking[] = [
  section("11111", "Low Grader", 0.42),
  section("22222", "High Grader", 0.88),
  section("22223", "High Grader", 0.88),
  section("33333", null, null),
  section("44444", "Few Grades", 0.97, { gradeCount: 9 }),
  section("55555", "Mid Grader", 0.6),
  section("66666", "Fourth Grader", 0.5),
];

const setup = () => {
  const rankingLoader = vi.fn(async (query: RankingQuery) => {
    const items = query.subject === "ENC" ? sections : [];
    return { items: items.slice(query.offset, query.offset + query.limit), total: items.length, limit: query.limit, offset: query.offset };
  });
  const navigate = vi.fn();
  render(<HomePage term="202701" rankingLoader={rankingLoader} navigate={navigate} />);
  return { rankingLoader, navigate, user: userEvent.setup() };
};

afterEach(() => window.localStorage.clear());

describe("home page", () => {
  it("submits a search", async () => {
    const { navigate, user } = setup();
    await user.type(screen.getByRole("searchbox"), "pre calc{Enter}");
    expect(navigate).toHaveBeenCalledExactlyOnceWith({ view: "search", q: "pre calc" });
  });

  it("lists every Gen Ed area and opens one in-app", async () => {
    const { navigate, user } = setup();
    const gened = screen.getByRole("region", { name: "I just need a GenEd" });
    expect(within(gened).getAllByRole("link").map((link) => link.textContent)).toEqual([
      "Communication",
      "Mathematics",
      "Natural Sciences",
      "Social Sciences",
      "Humanities",
      "Civics Literacy",
    ]);
    await user.click(within(gened).getByRole("link", { name: "Mathematics" }));
    expect(navigate).toHaveBeenCalledExactlyOnceWith({ view: "gened", area: "mathematics" });
  });
});

describe("live course preview", () => {
  it("shows the top three instructors of ENC 1101 with real history, one card each", async () => {
    const { rankingLoader } = setup();
    const preview = screen.getByRole("region", { name: "See it on a class everyone takes" });
    await within(preview).findByText("High Grader");
    const cards = Array.from(within(preview).getAllByRole("list")[0].children) as HTMLElement[];
    expect(cards).toHaveLength(3);
    expect(cards.map((card) => within(card).getByText(/Grader$/).textContent)).toEqual(["High Grader", "Mid Grader", "Fourth Grader"]);
    expect(cards[0]).toHaveTextContent("22222");
    expect(rankingLoader).toHaveBeenCalledWith(expect.objectContaining({ term: "202701", subject: "ENC", course_number: "1101" }), expect.anything());
    expect(within(preview).getByRole("link", { name: `See all ${sections.length} ENC 1101 sections` })).toHaveAttribute("href", "?q=ENC%201101");
  });

  it("switches the example course", async () => {
    const { rankingLoader, user } = setup();
    const course = screen.getByRole("button", { name: "MAC 1147" });
    await user.click(course);
    expect(course).toHaveAttribute("aria-pressed", "true");
    expect(rankingLoader).toHaveBeenCalledWith(expect.objectContaining({ subject: "MAC", course_number: "1147" }), expect.anything());
    expect(await screen.findByText("No MAC 1147 sections with enough instructor history yet")).toBeInTheDocument();
  });

  it("explains the first card and remembers when tips are hidden", async () => {
    const { user } = setup();
    const key = await screen.findByRole("list", { name: "How to read this card" });
    expect(within(key).getAllByRole("listitem")).toHaveLength(4);
    await user.click(screen.getByRole("button", { name: "Hide tips" }));
    expect(screen.queryByRole("list", { name: "How to read this card" })).not.toBeInTheDocument();
    expect(window.localStorage.getItem("easy-a:hide-reading-tips")).toBe("1");
    await user.click(screen.getByRole("button", { name: "How to read this" }));
    expect(screen.getByRole("list", { name: "How to read this card" })).toBeInTheDocument();
    expect(window.localStorage.getItem("easy-a:hide-reading-tips")).toBeNull();
  });

  it("starts with tips hidden for a returning student who hid them", async () => {
    window.localStorage.setItem("easy-a:hide-reading-tips", "1");
    setup();
    await screen.findByText("Mid Grader");
    expect(screen.queryByRole("list", { name: "How to read this card" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "How to read this" })).toBeInTheDocument();
  });
});

describe("GenEd menu beside the search field", () => {
  it("opens an area's list from the menu without submitting a search", async () => {
    const { navigate, user } = setup();
    const trigger = screen.getByRole("button", { name: "GenEd filters" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    await user.click(trigger);
    const popover = screen.getByRole("dialog", { name: "GenEd filters" });
    expect(trigger).toHaveAttribute("aria-controls", popover.id);
    expect(within(popover).getAllByRole("link")).toHaveLength(6);
    await user.click(within(popover).getByRole("link", { name: "Humanities" }));
    expect(navigate).toHaveBeenCalledExactlyOnceWith({ view: "gened", area: "humanities" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("supports keyboard opening, Escape and outside clicks with focus return", async () => {
    const { user } = setup();
    const trigger = screen.getByRole("button", { name: "GenEd filters" });
    trigger.focus();
    await user.keyboard("{Enter}");
    const popover = screen.getByRole("dialog");
    expect(within(popover).getByRole("link", { name: "Communication" })).toHaveFocus();
    await user.tab();
    expect(within(popover).getByRole("link", { name: "Mathematics" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    await user.click(trigger);
    await user.click(screen.getByRole("heading", { name: "See the grades before you register." }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
