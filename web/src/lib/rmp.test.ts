import { describe, expect, it, vi } from "vitest";

import { lastName, rmpKey, rmpLink } from "./rmp";

vi.mock("../data/rmp-profiles.json", () => ({
  default: { "ENC|n. volz": 3028196, "AMH|s. miller": 42 },
}));

const search = (q: string) => ({
  kind: "search",
  href: `https://www.ratemyprofessors.com/search/professors/1262?q=${q}`,
});

describe("rmpLink", () => {
  it("links a matched professor straight to their profile", () => {
    expect(rmpLink("N. Volz", "ENC")).toEqual({
      kind: "profile",
      href: "https://www.ratemyprofessors.com/professor/3028196",
    });
    expect(rmpLink("  n.   VOLZ ", " enc")).toEqual(rmpLink("N. Volz", "ENC"));
  });

  it("keys the profile on subject, since one initial and surname can be two people", () => {
    expect(rmpLink("S. Miller", "AMH")?.kind).toBe("profile");
    expect(rmpLink("S. Miller", "ENC")).toEqual(search("Miller"));
  });

  it.each([
    ["J. Doe", "Doe"],
    ["J. A. Doe", "Doe"],
    ["Jane Doe", "Jane%20Doe"],
    ["A. Van Der Berg", "Van%20Der%20Berg"],
    ["J. D’Ávila", "D%E2%80%99%C3%81vila"],
    ["Anne-Marie O'Neil", "Anne-Marie%20O'Neil"],
    ["李 明", "%E6%9D%8E%20%E6%98%8E"],
  ])("falls back to a USF search on the last name for %s", (name, q) => {
    expect(rmpLink(name, "ENC")).toEqual(search(q));
  });

  it.each([
    null, undefined, "", "   ", "Staff", " staff ", "STAFF", "TBA", "TBD",
    "Unknown", "Unavailable", "Not available", "Not announced", "N/A", "—", "Ambiguous",
    "Jane Doe / John Smith", "Jane Doe; John Smith", "Jane Doe & John Smith",
    "Jane Doe and John Smith", "Jane Doe\nJohn Smith",
  ])("omits blank, unavailable or ambiguous names: %s", (name) => {
    expect(rmpLink(name, "ENC")).toBeNull();
  });
});

describe("helpers", () => {
  it("builds the same key as the Python matcher", () => {
    expect(rmpKey(" enc ", "N.  Volz")).toBe("ENC|n. volz");
  });

  it("keeps a lone surname", () => {
    expect(lastName("Volz")).toBe("Volz");
  });

  it("drops the cut-off piece of a truncated schedule name", () => {
    expect(lastName("K. Mavridou-Hernan")).toBe("Mavridou");
    expect(lastName("R. Huligerepura Sh")).toBe("Huligerepura");
    expect(lastName("A. Van Der Berg")).toBe("Van Der Berg");
  });
});
