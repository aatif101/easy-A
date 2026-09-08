import { render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { SeatBadge } from "./Badges";
import { RankingDetails } from "./RankingDetails";
import { syntheticRankings } from "../fixtures/rankings";
import type { SeatInfo } from "../types/rankings";

const rankingWith = (seats: Partial<SeatInfo>) => ({ ...syntheticRankings[0], seats: { ...syntheticRankings[0].seats, ...seats } });
afterEach(() => vi.useRealTimers());

test.each(["fresh", "aging", "stale", "unavailable"] as const)("renders authoritative %s as visible text", (freshness) => {
  render(<SeatBadge ranking={rankingWith({ freshness, observed_at: "2000-01-01T00:00:00Z", age_seconds: 0 })} />);
  expect(screen.getByText(freshness[0].toUpperCase() + freshness.slice(1))).toBeVisible();
  expect(screen.getByText("Latest observed seats")).toBeVisible();
});

test("stale positive seats remain visible", () => {
  render(<SeatBadge ranking={rankingWith({ freshness: "stale", seats_remaining: 3 })} />);
  expect(screen.getByText("3 seats open")).toBeVisible();
  expect(screen.getByText("Stale observation; availability may have changed.")).toBeVisible();
});

test("null seats never become zero", () => {
  render(<SeatBadge ranking={rankingWith({ seats_remaining: null, freshness: "unavailable", observed_at: null, wait_seats_available: null })} />);
  expect(screen.getByText("Seat availability unavailable")).toBeVisible();
  expect(screen.getByText("Observation time unavailable")).toBeVisible();
  expect(screen.queryByText(/0 seats/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Waitlist:/)).not.toBeInTheDocument();
});

test("negative seats and waitlist retain their separate meanings", () => {
  render(<SeatBadge ranking={rankingWith({ seats_remaining: -2, wait_seats_available: 4 })} />);
  expect(screen.getByText("Over-enrolled by 2 (-2 seats remaining)")).toBeVisible();
  expect(screen.getByText("Waitlist: 4 spots available")).toBeVisible();
  expect(screen.queryByText("4 seats open")).not.toBeInTheDocument();
});

test.each([["fresh", "Updated 4 min ago"], ["stale", "Last checked 4 min ago"]] as const)("%s uses observed_at and absolute UTC tooltip", (freshness, expected) => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-09-08T16:00:00Z"));
  render(<SeatBadge ranking={rankingWith({ freshness, observed_at: "2026-09-08T11:56:00-04:00", age_seconds: 999999 })} />);
  expect(screen.getByText(expected)).toHaveAttribute("title", "2026-09-08 15:56:00 UTC");
});

test("expanded details show seat data separately from historical analytics", () => {
  render(<RankingDetails ranking={rankingWith({ freshness: "aging", enrollment: 27, capacity: 30, seats_remaining: 3, wait_seats_available: 4 })} id="details-test" />);
  const observation = screen.getByRole("region", { name: "Seat observation details" });
  expect(within(observation).getByText("Enrollment / capacity: 27 / 30")).toBeVisible();
  expect(within(observation).getByText("Aging")).toBeVisible();
  expect(within(observation).getByText("3 seats open")).toBeVisible();
  expect(within(observation).getByText("Waitlist: 4 spots available")).toBeVisible();
  expect(screen.getByText("Easiness")).toBeVisible();
});
