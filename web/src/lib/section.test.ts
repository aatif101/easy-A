import { describe, expect, it } from "vitest";

import { breakdown, section } from "../test/builders";
import { parseSearch } from "./search";
import { formatShare, seatsText, sortSections, termSpan, toSectionView } from "./section";

describe("parseSearch", () => {
  it("reads CRNs, course codes and subjects the way OASIS users type them", () => {
    expect(parseSearch("14028")).toEqual({ kind: "crn", crn: "14028" });
    expect(parseSearch("enc 1101")).toEqual({ kind: "course", subject: "ENC", courseNumber: "1101" });
    expect(parseSearch("cda3103")).toEqual({ kind: "course", subject: "CDA", courseNumber: "3103" });
    expect(parseSearch("CHM 2045L")).toEqual({ kind: "course", subject: "CHM", courseNumber: "2045L" });
    expect(parseSearch(" psy ")).toEqual({ kind: "subject", subject: "PSY" });
    expect(parseSearch("psychology")).toEqual({ kind: "unknown", text: "psychology" });
    expect(parseSearch("   ")).toEqual({ kind: "empty" });
  });
});

describe("toSectionView", () => {
  it("uses the current instructor's own A share and grade count", () => {
    const view = toSectionView(section("10001", "Jordan Alvarez", 0.79, { gradeCount: 57 }));
    expect(view.kind).toBe("instructor");
    expect(view.aShare).toBe(0.79);
    expect(view.caption).toBe("57 grades · 3 terms");
  });

  it("flags instructors below the scoring minimum as too few to trust", () => {
    const view = toSectionView(section("10002", "Jordan Alvarez", 0.95, { gradeCount: 12 }));
    expect(view.kind).toBe("thin");
    expect(view.caption).toContain("too few to trust");
  });

  it("never borrows another instructor's numbers when this one has no history", () => {
    const view = toSectionView(section("10003", "Priya Nair", null));
    expect(view.kind).toBe("no_history");
    expect(view.aShare).toBeNull();
    expect(view.history).toHaveLength(1);
  });

  it("treats Staff or a missing name as not announced", () => {
    expect(toSectionView(section("10004", null, null)).kind).toBe("unnamed");
    const staff = section("10005", "Staff", null, { breakdown: breakdown({ current_instructor: null }) });
    expect(toSectionView(staff).instructor).toBe("TBA");
  });

  it("separates lab sections and courses with no grade history", () => {
    expect(toSectionView(section("10006", "A", null, { breakdown: breakdown({ status: "lab_section" }) })).kind).toBe("lab");
    expect(toSectionView(section("10007", "A", null, { breakdown: null })).kind).toBe("none");
  });
});

describe("sortSections", () => {
  it("puts real instructor history first, highest A share first", () => {
    const rows = [
      section("1", "Thin", 0.99, { gradeCount: 5 }),
      section("2", null, null),
      section("3", "Low", 0.4),
      section("4", "High", 0.8),
    ].map((ranking) => ({ ranking, view: toSectionView(ranking) }));
    expect(sortSections(rows, "a_share").map(({ ranking }) => ranking.crn)).toEqual(["4", "3", "1", "2"]);
    expect(sortSections(rows, "crn").map(({ ranking }) => ranking.crn)).toEqual(["1", "2", "3", "4"]);
  });
});

describe("formatting", () => {
  it("formats shares, seats and term spans", () => {
    expect(formatShare(0.789)).toBe("79%");
    expect(termSpan("202408", "202601")).toBe("Fall 2024 – Spring 2026");
    expect(termSpan("202505", "202505")).toBe("Summer 2025");
    const view = toSectionView(section("1", "A", 0.5));
    expect(seatsText({ ...view, seatsOpen: 0 })).toBe("Full");
    expect(seatsText({ ...view, seatsOpen: 4, seatsCapacity: 19 })).toBe("4/19");
  });
});
