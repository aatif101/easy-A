import { describe, expect, it } from "vitest";

import { readRoute, routeHref, type Route } from "./route";

describe("instructor course routes", () => {
  it("round-trips names with punctuation and query-string characters", () => {
    const route: Route = { view: "search", q: "ENC 1101", instructor: { courseId: 12, name: "J. O'Neil & García+Lopez" } };
    expect(readRoute(routeHref(route))).toEqual(route);
  });

  it.each([
    "?q=ENC%201101&instructor=Smith",
    "?q=ENC%201101&course_id=-1&instructor=Smith",
    "?q=ENC%201101&course_id=1.5&instructor=Smith",
    "?q=ENC%201101&course_id=Infinity&instructor=Smith",
    "?q=ENC%201101&course_id=2147483648&instructor=Smith",
    "?q=ENC%201101&course_id=1&instructor=%20",
    `?q=ENC%201101&course_id=1&instructor=${"x".repeat(256)}`,
  ])("ignores malformed instructor selections: %s", search => {
    expect(readRoute(search)).toEqual({ view: "search", q: "ENC 1101" });
  });

  it("does not carry a professor selection into a free-text name search", () => {
    expect(readRoute("?q=smith&course_id=1&instructor=Smith")).toEqual({ view: "search", q: "smith" });
  });
});
