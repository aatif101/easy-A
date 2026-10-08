import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { HomePage } from "./HomePage";

const setup = () => {
  const navigate = vi.fn();
  render(<HomePage navigate={navigate} />);
  return { navigate, user: userEvent.setup() };
};

describe("home page doors", () => {
  it("offers a class search, every Gen Ed area and a professor search", () => {
    setup();
    expect(screen.getByRole("heading", { name: "I know which class I need" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "I just need a GenEd" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "I'm checking a professor" })).toBeInTheDocument();
    const gened = screen.getByRole("region", { name: "I just need a GenEd" });
    const links = within(gened).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual([
      "Communication",
      "Mathematics",
      "Natural Sciences",
      "Social Sciences",
      "Humanities",
      "Civics Literacy",
    ]);
    expect(within(gened).getByRole("link", { name: "Humanities" })).toHaveAttribute("href", "?gened=humanities");
  });

  it("opens a Gen Ed area in-app", async () => {
    const { navigate, user } = setup();
    await user.click(screen.getByRole("link", { name: "Mathematics" }));
    expect(navigate).toHaveBeenCalledExactlyOnceWith({ view: "gened", area: "mathematics" });
  });

  it("submits a search", async () => {
    const { navigate, user } = setup();
    await user.type(screen.getByRole("searchbox"), "pre calc{Enter}");
    expect(navigate).toHaveBeenCalledExactlyOnceWith({ view: "search", q: "pre calc" });
  });

  it("sends the professor door to the search field", async () => {
    const { user } = setup();
    await user.click(screen.getByRole("button", { name: "Search a professor" }));
    expect(screen.getByRole("searchbox")).toHaveFocus();
  });

  it("links to the score guide", async () => {
    const { navigate, user } = setup();
    const link = screen.getByRole("link", { name: "How to read the score" });
    expect(link).toHaveAttribute("href", "?guide");
    await user.click(link);
    expect(navigate).toHaveBeenCalledExactlyOnceWith({ view: "guide" });
  });
});

describe("GenEd menu beside the search field", () => {
  it("opens an area's list from the menu without submitting a search", async () => {
    const { navigate, user } = setup();
    const trigger = screen.getByRole("button", { name: "GenEd filters" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(trigger);
    const popover = screen.getByRole("dialog", { name: "GenEd filters" });
    expect(trigger).toHaveAttribute("aria-controls", popover.id);
    expect(within(popover).getAllByRole("link")).toHaveLength(6);
    await user.click(within(popover).getByRole("link", { name: "Humanities" }));
    expect(navigate).toHaveBeenCalledExactlyOnceWith({ view: "gened", area: "humanities" });
  });

  it("supports keyboard opening, Escape and outside clicks with focus return", async () => {
    const { user } = setup();
    const trigger = screen.getByRole("button", { name: "GenEd filters" });
    trigger.focus();
    await user.keyboard("{Enter}");
    const popover = screen.getByRole("dialog");
    expect(within(popover).getByRole("link", { name: "Communication" })).toHaveFocus();
    await user.tab();
    expect(within(popover).getByRole("link", { name: "Mathematics" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    await user.click(trigger);
    await user.click(screen.getByRole("heading", { name: "See the grades before you register." }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
