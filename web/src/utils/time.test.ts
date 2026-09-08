import { describe, expect, test } from "vitest";
import { formatAbsoluteTime, formatRelativeTime } from "./time";

const now = Date.parse("2026-09-08T16:00:00Z");
describe("timestamp formatting", () => {
  test.each([[0, "just now"], [59, "just now"], [60, "1 min ago"], [240, "4 min ago"], [1320, "22 min ago"], [3600, "1 hr ago"], [7200, "2 hr ago"], [86400, "1 day ago"], [172800, "2 days ago"]])("formats age %s seconds", (seconds, expected) => {
    expect(formatRelativeTime(new Date(now - Number(seconds) * 1000).toISOString(), now)).toBe(expected);
  });
  test.each([null, undefined, "", "invalid", "2026-09-08T12:00:00", "2026-13-40T00:00:00Z", "2026-02-30T00:00:00Z", "2026-09-08T24:00:00Z"])("handles unavailable input %s", (input) => {
    expect(formatRelativeTime(input, now)).toBe("Unavailable");
    expect(formatAbsoluteTime(input)).toBe("Unavailable");
  });
  test("offsets identify the same instant", () => {
    expect(formatRelativeTime("2026-09-08T11:56:00-04:00", now)).toBe("4 min ago");
    expect(formatAbsoluteTime("2026-09-08T11:56:00-04:00")).toBe("2026-09-08 15:56:00 UTC");
  });
  test("future observation clamps to just now", () => {
    expect(formatRelativeTime("2026-09-08T16:01:00Z", now)).toBe("just now");
  });
  test("invalid clock is unavailable", () => {
    expect(formatRelativeTime("2026-09-08T16:00:00Z", NaN)).toBe("Unavailable");
  });
});
