import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { SyncStatus } from "./SyncStatus";
import type { SyncStatus as SyncStatusData, SyncStatusLoader } from "../types/rankings";

const NOW = new Date("2027-01-15T12:00:00Z");
const fourMinutesAgo = "2027-01-15T11:56:00Z";

const status = (overrides: Partial<SyncStatusData> = {}): SyncStatusData => ({
  term: "202701",
  last_success_at: fourMinutesAgo,
  last_run_at: fourMinutesAgo,
  last_status: "succeeded",
  last_error_kind: null,
  last_records_failed: 0,
  failures_last_24h: 0,
  in_registration_window: true,
  cadence_seconds: 3600,
  stale_after_seconds: 7200,
  is_stale: false,
  as_of: "2027-01-15T12:00:00Z",
  ...overrides,
});

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(NOW);
});
afterEach(() => vi.useRealTimers());

test("a fresh status shows a relative time with the UTC time as its title", async () => {
  render(<SyncStatus term="202701" loader={async () => status()} />);
  const updated = await screen.findByText("Updated 4 min ago");
  expect(updated).toHaveAttribute("title", "2027-01-15 11:56:00 UTC");
  expect(screen.queryByText("Seat data may be out of date.")).not.toBeInTheDocument();
});

test("is_stale from the API renders the amber warning", async () => {
  render(<SyncStatus term="202701" loader={async () => status({ is_stale: true })} />);
  const warning = await screen.findByText("Seat data may be out of date.");
  expect(warning).toHaveAttribute("role", "status");
});

test("a null last_success_at says the data was never verified and shows no Updated time", async () => {
  render(<SyncStatus term="202701" loader={async () => status({ last_success_at: null })} />);
  expect(await screen.findByText("Seat data has not been verified by the live sync yet.")).toBeVisible();
  expect(screen.queryByText(/Updated/)).not.toBeInTheDocument();
});

test("a failed request is announced and can be retried", async () => {
  const user = userEvent.setup();
  const loader = vi.fn<SyncStatusLoader>().mockRejectedValueOnce(new Error("offline")).mockResolvedValue(status());
  render(<SyncStatus term="202701" loader={loader} />);
  await screen.findByText("Data freshness unavailable.");
  await user.click(screen.getByRole("button", { name: "Retry freshness" }));
  expect(await screen.findByText("Updated 4 min ago")).toBeVisible();
  expect(loader).toHaveBeenCalledTimes(2);
});

test("synthetic mode never shows an Updated time", async () => {
  const loader = vi.fn<SyncStatusLoader>(async () => status());
  render(<SyncStatus term="202701" loader={loader} synthetic />);
  expect(await screen.findByText("Synthetic demo data: seat freshness is not live.")).toBeVisible();
  await waitFor(() => expect(screen.queryByText(/Updated/)).not.toBeInTheDocument());
});
