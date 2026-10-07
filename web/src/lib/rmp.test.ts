import { describe, expect, it } from "vitest";

import { rmpSearchUrl } from "./rmp";

describe("USF Rate My Professors search", () => {
  it.each([
    ["Jane Doe", "Jane%20Doe"],
    ["Doe, Jane A.", "Doe%2C%20Jane%20A."],
    ["Anne-Marie O'Neil", "Anne-Marie%20O'Neil"],
    ["José D’Ávila", "Jos%C3%A9%20D%E2%80%99%C3%81vila"],
    ["李 明", "%E6%9D%8E%20%E6%98%8E"],
    [" Jane Doe ", "Jane%20Doe"],
  ])("encodes %s in the school 1262 search", (name, encoded) => {
    expect(rmpSearchUrl(name)).toBe(`https://www.ratemyprofessors.com/search/professors/1262?q=${encoded}`);
  });

  it.each([
    null, undefined, "", "   ", "Staff", " staff ", "STAFF", "TBA", "TBD",
    "Unknown", "Unavailable", "Not available", "Not announced", "N/A", "—", "Ambiguous",
    "Jane Doe / John Smith", "Jane Doe; John Smith", "Jane Doe & John Smith",
    "Jane Doe and John Smith", "Jane Doe\nJohn Smith",
  ])("omits blank, unavailable or ambiguous names: %s", (name) => {
    expect(rmpSearchUrl(name)).toBeNull();
  });
});
