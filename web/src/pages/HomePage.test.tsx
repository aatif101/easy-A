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
