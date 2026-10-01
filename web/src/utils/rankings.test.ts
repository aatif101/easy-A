import { expect, test } from "vitest";
import { syntheticRankings } from "../fixtures/rankings";
import type { SectionRanking } from "../types/rankings";
import {
  formatGradeCount,
  formatTermCount,
  formatTermRange,
  formatTermShort,
  isNamedInstructor,
} from "./rankings";

test("formatTermShort maps Banner suffixes to season plus two-digit year", () => {
  expect(formatTermShort("202501")).toBe("Spr 25");
  expect(formatTermShort("202505")).toBe("Sum 25");
  expect(formatTermShort("202408")).toBe("Fall 24");
});

test("formatTermShort fails closed to the raw code", () => {
  expect(formatTermShort("202603")).toBe("202603");
  expect(formatTermShort("2025")).toBe("2025");
  expect(formatTermShort("")).toBe("");
});

test("formatTermRange uses one label for a single term and an en dash otherwise", () => {
  expect(formatTermRange("202508", "202508")).toBe("Fall 25");
  expect(formatTermRange("202501", "202601")).toBe("Spr 25–Spr 26");
});

test("count helpers are plural-aware and round grades", () => {
  expect(formatGradeCount(1)).toBe("1 grade");
  expect(formatGradeCount(0.6)).toBe("1 grade");
  expect(formatGradeCount(175)).toBe("175 grades");
  expect(formatTermCount(1)).toBe("1 term");
  expect(formatTermCount(3)).toBe("3 terms");
});

test("isNamedInstructor is true only for a real named person", () => {
  const base: SectionRanking = syntheticRankings[4];
  expect(isNamedInstructor({ ...base, instructor: "X. Ou" })).toBe(true);
  expect(isNamedInstructor({ ...base, instructor: "staff" })).toBe(false);
  expect(isNamedInstructor({ ...base, instructor: " STAFF " })).toBe(false);
  expect(isNamedInstructor({ ...base, instructor: null })).toBe(false);
  expect(
    isNamedInstructor({
      ...base,
      instructor: null,
      instructor_provenance: { ...base.instructor_provenance, freshness: "historical", detail: "ambiguous match" },
    }),
  ).toBe(false);
  expect(
    isNamedInstructor({
      ...base,
      instructor: null,
      instructor_provenance: { ...base.instructor_provenance, freshness: "unavailable", detail: null },
    }),
  ).toBe(false);
});
