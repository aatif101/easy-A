import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import { CoverageNotice } from "./CoverageNotice";
import type { CourseCoverage, CoverageLoader } from "../types/rankings";

const observed: CourseCoverage = { subject: "CHM", course_number: "2045L", catalog_present: true, section_count: 4, latest_observed_at: "2026-09-08T16:00:00Z", status: "observed" };
const renderCoverage = (items: CourseCoverage[]) => render(<CoverageNotice term="202701" subject="CHM" courseNumber="2045L" loader={async () => items} />);

test.each([{ items: [] }, { items: [observed] }])("observed or absent target adds no blocking claim: %j", async ({ items }) => {
  renderCoverage(items);
  await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
});

test("configured course without sections", async () => {
  renderCoverage([{ ...observed, section_count: 0, status: "missing" }]);
  expect(await screen.findByText(/No current sections have been observed for this configured course/)).toBeVisible();
});

test("configured course without catalog", async () => {
  renderCoverage([{ ...observed, catalog_present: false, section_count: 0, status: "missing" }]);
  expect(await screen.findByText(/Catalog information is not currently available for this configured course/)).toBeVisible();
});

test("coverage failure is announced and can be retried", async () => {
  const user = userEvent.setup();
  const loader = vi.fn<CoverageLoader>().mockRejectedValueOnce(new Error("offline")).mockResolvedValue([]);
  render(<CoverageNotice term="202701" loader={loader} />);
  await screen.findByText("Coverage information unavailable. You can still search sections.");
  await user.click(screen.getByRole("button", { name: "Retry coverage" }));
  await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
  expect(loader).toHaveBeenCalledTimes(2);
});

test("coverage is reused for searches but term changes reject late responses", async () => {
  let finish!: (items: CourseCoverage[]) => void;
  const loader = vi.fn<CoverageLoader>().mockImplementationOnce(() => new Promise(resolve => { finish = resolve; })).mockResolvedValue([]);
  const { rerender } = render(<CoverageNotice key="202701" term="202701" subject="CHM" courseNumber="2045L" loader={loader} />);
  rerender(<CoverageNotice key="202701" term="202701" subject="PHY" courseNumber="2048" loader={loader} />);
  expect(loader).toHaveBeenCalledTimes(1);
  rerender(<CoverageNotice key="202801" term="202801" subject="CHM" courseNumber="2045L" loader={loader} />);
  await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
  await act(async () => finish([{ ...observed, catalog_present: false }]));
  expect(screen.queryByText(/Catalog information/)).not.toBeInTheDocument();
  expect(loader).toHaveBeenLastCalledWith("202801", expect.any(AbortSignal));
});
