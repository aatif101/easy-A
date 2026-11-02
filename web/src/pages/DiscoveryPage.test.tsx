import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CourseMatch, DiscoveryLoader, DiscoveryResponse, HistoryResponse } from "../types/search";
import { section } from "../test/builders";
import type { RankingQuery } from "../types/rankings";
import { DiscoveryPage } from "./DiscoveryPage";

const course: CourseMatch = { course_id: 1, subject: "ENC", course_number: "1101", title: "Composition I", catalog_edition: "2026-2027", current_sections: 2 };
const note = "College identity is unavailable. Matching names across courses are not proof of the same person.";
const matches: DiscoveryResponse = {
  as_of: "2026-10-07T12:00:00Z",
  kind: "text", subject: "", course_number: "", crn: null, courses: [course, { ...course, course_id: 2, subject: "ABC", title: "Program Design", current_sections: 0 }],
  instructors: [1, 2].map(id => ({ ...course, course_id: id, name: "J. Smith", current_sections: id === 1 ? 1 : 0, historical_sections: 3, observed_at: "2026-10-07T12:00:00Z" })),
  course_total: 2, instructor_total: 2, offset: 0, limit: 20, identity_note: note,
};
const history: HistoryResponse = { course, name: "J. Smith", status: "insufficient", a_share: 0.5, observed_grade_count: 12, counts: { a: 6, b: 6 }, terms: ["202508", "202601"], items: [{ term: "202601", crn: "10001", counts: { a: 6, b: 6 }, source: "usf_infocenter", source_hash: "a".repeat(64), ingested_at: "2026-10-07T12:00:00Z" }], total: 1, offset: 0, limit: 20, identity_note: note };

function setup(data = matches, gradeData = history) {
  const discoveryLoader = vi.fn<DiscoveryLoader>(async () => data);
  const historyLoader = vi.fn(async () => gradeData);
  const rankingLoader = vi.fn(async (query: RankingQuery) => {
    const items = query.instructor
      ? [section("20001", query.instructor, 0.5, { subject: query.subject, course_number: query.course_number })]
      : [section("10001", "J. Smith", 0.6, { subject: query.subject, course_number: query.course_number }), section("10002", null, null, { subject: query.subject, course_number: query.course_number })];
    return { items, total: items.length, limit: query.limit, offset: query.offset };
  });
  const navigate = vi.fn();
  render(<DiscoveryPage term="202701" q="1101" discoveryLoader={discoveryLoader} historyLoader={historyLoader} rankingLoader={rankingLoader} navigate={navigate} />);
  return { discoveryLoader, historyLoader, rankingLoader, navigate };
}

const matchesFor = { term: "202701", limit: 200, offset: 0 };

describe("expanded search", () => {
  it("lists the offered sections of matching courses with CRNs in the shared table", async () => {
    const { rankingLoader, navigate } = setup();
    const table = await screen.findByRole("table");
    expect(within(table).getByText("10001")).toBeInTheDocument();
    expect(within(table).getByRole("button", { name: "Copy CRN 10002" })).toBeInTheDocument();
    expect(within(table).getByText("Not assigned")).toBeInTheDocument();
    expect(rankingLoader).toHaveBeenCalledWith({ ...matchesFor, subject: "ENC", course_number: "1101" }, expect.any(AbortSignal));
    // The course with no current sections is not requested.
    expect(rankingLoader).not.toHaveBeenCalledWith(expect.objectContaining({ subject: "ABC" }), expect.anything());
    await userEvent.click(within(table).getAllByRole("link", { name: "ENC 1101" })[0]);
    expect(navigate).toHaveBeenCalledWith({ view: "search", q: "ENC 1101" });
  });

  it("loads only a matched instructor's sections when their course did not match", async () => {
    const { rankingLoader } = setup({ ...matches, courses: [], course_total: 0 });
    const table = await screen.findByRole("table");
    expect(within(table).getByText("20001")).toBeInTheDocument();
    expect(rankingLoader).toHaveBeenCalledWith({ ...matchesFor, subject: "ENC", course_number: "1101", course_id: 1, instructor: "J. Smith" }, expect.any(AbortSignal));
    expect(rankingLoader).toHaveBeenCalledTimes(1);
  });

  it("says so when nothing matching is offered and opens the past records", async () => {
    setup({ ...matches, courses: [{ ...course, current_sections: 0 }], instructors: [], instructor_total: 0, course_total: 1 });
    expect(await screen.findByText('Nothing matching "1101" is offered in Spring 2027')).toBeInTheDocument();
    expect(screen.getByText(/Not offered in Spring 2027/)).toBeVisible();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("opens historical-only professor history with raw distribution, denominator, terms and provenance", async () => {
    const { historyLoader } = setup();
    await screen.findByRole("table");
    await userEvent.click(screen.getByText("Past grade records for these matches"));
    expect(screen.getByText(note)).toBeInTheDocument();
    const names = screen.getAllByText("J. Smith").filter(name => name.classList.contains("font-semibold"));
    expect(names).toHaveLength(2);
    for (const name of names) {
      expect(name.nextElementSibling).toHaveAttribute("href", expect.stringContaining("ratemyprofessors.com"));
    }
    const buttons = screen.getAllByRole("button", { name: /Grade history for J. Smith/ });
    buttons[1].focus();
    await userEvent.keyboard("{Enter}");
    expect(historyLoader).toHaveBeenCalledWith("202701", 2, "J. Smith", 0, expect.any(AbortSignal));
    expect(await screen.findByText(/12 observed A–F grades · too few to trust/)).toBeInTheDocument();
    expect(screen.getByText(/Covered terms: Fall 2025, Spring 2026/)).toBeInTheDocument();
    expect(screen.getByText(/Historical record/)).toHaveTextContent("CRN 10001");
    expect(screen.getByText(/Source: usf_infocenter/)).toHaveTextContent("Imported 10/7/2026");
    expect(buttons[1]).toHaveAttribute("aria-expanded", "true");
  });

  it.each(["unavailable", "no_letter_grades"])("preserves %s evidence states", async status => {
    setup(matches, { ...history, status, a_share: null, observed_grade_count: 0, total: 0, items: [], terms: [] });
    await screen.findByRole("table");
    await userEvent.click(screen.getAllByRole("button", { name: "Grade history for ENC 1101" })[0]);
    expect(await screen.findByText(status === "unavailable" ? /No attributable grade history/ : /No letter-grade history/)).toBeInTheDocument();
    expect(screen.queryByText(/50% A/)).not.toBeInTheDocument();
  });

  it("paginates server results and cancels the previous request", async () => {
    const { discoveryLoader } = setup({ ...matches, course_total: 25 });
    await userEvent.click(await screen.findByRole("button", { name: "Next results" }));
    expect(discoveryLoader).toHaveBeenLastCalledWith("202701", "1101", 20, expect.any(AbortSignal));
    expect(discoveryLoader.mock.calls[0]?.length).toBe(4);
  });

  it("shows an empty result explanation", async () => {
    setup({ ...matches, courses: [], instructors: [], course_total: 0, instructor_total: 0 });
    expect(await screen.findByText('Nothing matches "1101"')).toBeInTheDocument();
  });

  it("provides loading and retry and aborts stale query requests", async () => {
    const signals: AbortSignal[] = [];
    const loader = vi.fn((_term: string, q: string, _offset: number, signal: AbortSignal) => {
      signals.push(signal);
      return q === "first" ? new Promise<DiscoveryResponse>(() => {}) : Promise.reject(new Error("offline"));
    });
    const props = { term: "202701", discoveryLoader: loader, historyLoader: vi.fn(async () => history), rankingLoader: vi.fn(async (query: RankingQuery) => ({ items: [], total: 0, limit: query.limit, offset: query.offset })), navigate: vi.fn() };
    const { rerender } = render(<DiscoveryPage {...props} q="first" />);
    expect(screen.getByText("Searching courses and instructors…")).toBeInTheDocument();
    rerender(<DiscoveryPage {...props} q="second" />);
    await userEvent.click(await screen.findByRole("button", { name: /try again/i }));
    expect(signals[0].aborted).toBe(true);
    expect(loader).toHaveBeenCalledTimes(3);
  });
});
