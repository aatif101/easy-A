import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CourseMatch, DiscoveryLoader, DiscoveryResponse, HistoryResponse } from "../types/search";
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
  const navigate = vi.fn();
  render(<DiscoveryPage term="202701" q="1101" discoveryLoader={discoveryLoader} historyLoader={historyLoader} navigate={navigate} />);
  return { discoveryLoader, historyLoader, navigate };
}

describe("expanded search", () => {
  it("labels ambiguous course and instructor matches and preserves selection navigation", async () => {
    const { navigate } = setup();
    const courses = await screen.findByRole("region", { name: "Course results" });
    const instructors = screen.getByRole("region", { name: "Instructor results" });
    expect(within(courses).getByRole("heading", { name: /ABC 1101/ })).toBeInTheDocument();
    expect(within(courses).getByText(/No current sections/)).toBeInTheDocument();
    expect(within(instructors).getAllByText(/Listed instructor: J. Smith/)).toHaveLength(2);
    expect(within(instructors).getByText(note)).toBeInTheDocument();
    await userEvent.click(within(courses).getByRole("link", { name: "Compare current sections" }));
    expect(navigate).toHaveBeenCalledWith({ view: "search", q: "ENC 1101" });
  });

  it("opens historical-only professor history with raw distribution, denominator, terms and provenance", async () => {
    const { historyLoader } = setup();
    const instructors = await screen.findByRole("region", { name: "Instructor results" });
    const buttons = within(instructors).getAllByRole("button", { name: /Grade history for J. Smith/ });
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
    await userEvent.click((await screen.findAllByRole("button", { name: "Grade history for ENC 1101" }))[0]);
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
    const props = { term: "202701", discoveryLoader: loader, historyLoader: vi.fn(async () => history), navigate: vi.fn() };
    const { rerender } = render(<DiscoveryPage {...props} q="first" />);
    expect(screen.getByText("Searching courses and instructors…")).toBeInTheDocument();
    rerender(<DiscoveryPage {...props} q="second" />);
    await userEvent.click(await screen.findByRole("button", { name: /try again/i }));
    expect(signals[0].aborted).toBe(true);
    expect(loader).toHaveBeenCalledTimes(3);
  });
});
