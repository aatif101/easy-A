import { describe, expect, it } from "vitest";

import { breakdown, section } from "../test/builders";
import { parseSearch } from "./search";
import type { Meeting } from "../types/rankings";
import { formatShare, gradeShares, seatsText, sortSections, termSpan, toSectionView, waitlistText } from "./section";

const meet = (days: string, start: string | null = null, end: string | null = null, isExam = false, building: string | null = null, room: string | null = null): Meeting => ({
  days,
  start_time: start,
  end_time: end,
  building,
  room,
  is_exam: isExam,
});

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
    expect(toSectionView(staff).instructor).toBe("Not assigned");
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

  it("orders by course code by default and by earliest class time on request", () => {
    const rows = [
      section("3", "A", 0.9, { subject: "PHY", course_number: "2048", meetings: [meet("MW", "08:00", "09:15")] }),
      section("2", "B", 0.2, { subject: "MAC", course_number: "2311", meetings: [] }),
      section("1", "C", 0.5, { subject: "MAC", course_number: "2311", meetings: [meet("TR", "14:00", "15:15")] }),
    ].map((ranking) => ({ ranking, view: toSectionView(ranking) }));
    expect(sortSections(rows, "course").map(({ ranking }) => ranking.crn)).toEqual(["1", "2", "3"]);
    expect(sortSections(rows, "schedule").map(({ ranking }) => ranking.crn)).toEqual(["3", "1", "2"]);
  });
});

describe("formatting", () => {
  it("formats shares, seats and term spans", () => {
    expect(formatShare(0.789)).toBe("79%");
    expect(termSpan("202408", "202601")).toBe("Fall 2024 – Spring 2026");
    expect(termSpan("202505", "202505")).toBe("Summer 2025");
    const view = toSectionView(section("1", "A", 0.5));
    expect(seatsText({ ...view, seatsOpen: 0 })).toBe("Full");
    expect(seatsText({ ...view, seatsOpen: 4, seatsCapacity: 19 })).toBe("4 of 19");
    expect(waitlistText({ ...view, seatsOpen: 0, waitSeats: 1 })).toBe("1 waitlist spot");
    expect(waitlistText({ ...view, seatsOpen: 3, waitSeats: 5 })).toBeNull();
  });

  it("keeps every grade share only when the API sent them all", () => {
    const row = toSectionView(section("1", "A", 0.5)).history[0];
    expect(gradeShares(row)?.b).toBeCloseTo(0.25);
    expect(gradeShares({ ...row, b_share: undefined })).toBeNull();
  });
});

describe("schedule text", () => {
  const schedule = (meetings: Meeting[], delivery = "CL") =>
    toSectionView(section("1", "A", 0.5, { meetings, modality: { ...section("1", "A", 0.5).modality, delivery_method: delivery } }));

  it("shows class meetings and moves exams to the details", () => {
    const view = schedule([meet("MW", "09:30", "10:45", false, "CHE", "101A"), meet("F", "11:00", "11:50"), meet("S", "07:30", "09:30", true, "EXAM", "F100")]);
    expect(view.schedule).toEqual(["MW 9:30–10:45am", "F 11:00–11:50am"]);
    expect(view.meetingDetails).toEqual(["MW 9:30–10:45am · CHE 101A", "F 11:00–11:50am", "Exam: S 7:30–9:30am"]);
  });

  it("marks am and pm only where they change", () => {
    expect(schedule([meet("TR", "11:00", "12:15")]).schedule).toEqual(["TR 11:00am–12:15pm"]);
    expect(schedule([meet("MW", "19:00", "20:45")]).schedule).toEqual(["MW 7:00–8:45pm"]);
  });

  it("shows days alone when the time is unknown and never invents one", () => {
    expect(schedule([meet("TR"), meet("F")]).schedule).toEqual(["TR, F"]);
  });

  it("says when there is no meeting to show", () => {
    expect(schedule([], "AD").schedule).toEqual(["No set meeting time"]);
    expect(schedule([meet("TBA")]).schedule).toEqual(["Time not listed"]);
  });
});
