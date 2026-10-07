import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { HomePage } from "./HomePage";
import type { RankingQuery } from "../types/rankings";

const setup = () => {
  const rankingLoader = vi.fn(async (query: RankingQuery) => ({ items: [], total: 0, limit: query.limit, offset: query.offset }));
  const navigate = vi.fn();
  render(<HomePage term="202701" rankingLoader={rankingLoader} navigate={navigate} />);
  return { rankingLoader, navigate, user: userEvent.setup() };
};

describe("GenEd filter popover", () => {
  it("hides options initially and applies or clears a selection without submitting search", async () => {
    const { rankingLoader, navigate, user } = setup();
    const trigger = screen.getByRole("button", { name: "GenEd filters" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: "Mathematics" })).not.toBeInTheDocument();
    await user.click(trigger);
    const popover = screen.getByRole("dialog", { name: "GenEd filters" });
    expect(trigger).toHaveAttribute("aria-controls", popover.id);
    await user.click(within(popover).getByRole("button", { name: "Mathematics" }));
    expect(screen.getByRole("heading", { name: "Mathematics sections with high A rates" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    await waitFor(() => {
      for (const code of ["SGEM", "UGEM"]) {
        expect(rankingLoader).toHaveBeenCalledWith(expect.objectContaining({ term: "202701", gened_code: code }), expect.anything());
      }
    });
    await user.click(trigger);
    expect(screen.getByRole("button", { name: "Mathematics" })).toHaveAttribute("aria-pressed", "true");
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(screen.getByRole("heading", { name: "Social Sciences sections with high A rates" })).toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("supports keyboard opening, tabbing, selection and Escape with focus return", async () => {
    const { user } = setup();
    const trigger = screen.getByRole("button", { name: "GenEd filters" });
    trigger.focus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("button", { name: "Social Sciences" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Humanities" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("heading", { name: "Humanities sections with high A rates" })).toBeInTheDocument();
    expect(trigger).toHaveFocus();
    await user.keyboard(" ");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("dismisses outside clicks and preserves normal search submission", async () => {
    const { user, navigate } = setup();
    await user.click(screen.getByRole("button", { name: "GenEd filters" }));
    await user.click(screen.getByRole("heading", { name: "Who gives the most A's?" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.type(screen.getByRole("searchbox"), "ENC 1101{Enter}");
    expect(navigate).toHaveBeenCalledExactlyOnceWith({ view: "search", q: "ENC 1101" });
  });
});
