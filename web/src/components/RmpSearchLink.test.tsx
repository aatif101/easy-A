import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { toSectionView } from "../lib/section";
import { breakdown, historyRow, section } from "../test/builders";
import { InstructorHistory } from "./InstructorHistory";
import { RmpSearchLink } from "./RmpSearchLink";
import { SectionTable } from "./SectionTable";

const label = (name: string) => `Search for ${name} on Rate My Professors`;

describe("RmpSearchLink", () => {
  it("labels the destination as a search and opens it securely in a new tab", async () => {
    const user = userEvent.setup();
    render(<RmpSearchLink instructor="Jane Doe" />);
    const link = screen.getByRole("link", { name: label("Jane Doe") });
    expect(link).toHaveTextContent("RMP ↗");
    expect(link).toHaveAttribute("href", "https://www.ratemyprofessors.com/search/professors/1262?q=Jane%20Doe");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    await user.tab();
    expect(link).toHaveFocus();
  });

  it.each([null, "", " ", "Staff", "TBA", "Unavailable", "Ambiguous", "Jane Doe / John Smith"])(
    "has no link for %s", (instructor) => {
      render(<RmpSearchLink instructor={instructor} />);
      expect(screen.queryByRole("link")).not.toBeInTheDocument();
    },
  );
});

describe("current instructor displays", () => {
  it.each([0.8, null])("links named instructors in both table and cards, including without history (%s)", (share) => {
    const ranking = section("12345", "Jane Doe", share);
    const { container } = render(<SectionTable rows={[{ ranking, view: toSectionView(ranking) }]} />);
    const table = screen.getByRole("table");
    const cards = container.querySelector("ul")!;
    for (const display of [table, cards]) {
      const link = within(display).getByRole("link", { name: label("Jane Doe") });
      expect(link.previousElementSibling).toHaveTextContent("Jane Doe");
    }
  });

  it.each([null, "", "   ", "Staff", " staff ", "TBA", "Unavailable", "Jane Doe / John Smith"])(
    "omits current links in both layouts for %s", (name) => {
      const ranking = section("12345", name, null, { breakdown: breakdown() });
      render(<SectionTable rows={[{ ranking, view: toSectionView(ranking) }]} />);
      expect(screen.queryByRole("link")).not.toBeInTheDocument();
    },
  );

  it.each(["unavailable", "ambiguous latest instructor state: Jane Doe / John Smith"])(
    "does not link unavailable provenance (%s), even if a display name remains", (detail) => {
      const ranking = section("12345", "Jane Doe", null, {
        instructor_provenance: { freshness: "unavailable", source: "section_instructors", source_term: "202701", detail },
      });
      render(<SectionTable rows={[{ ranking, view: toSectionView(ranking) }]} />);
      expect(screen.queryByRole("link")).not.toBeInTheDocument();
    },
  );

  it("keeps historical search links available when the current assignment is ambiguous", async () => {
    const ranking = section("12345", null, null, {
      instructor_provenance: {
        freshness: "unavailable", source: "section_instructors", source_term: "202701",
        detail: "ambiguous latest instructor state: Jane Doe / John Smith",
      },
      breakdown: breakdown({ instructors: [historyRow("Past Teacher", 0.6, 100)] }),
    });
    render(<SectionTable rows={[{ ranking, view: toSectionView(ranking) }]} />);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Compare instructors for CRN 12345" }));
    expect(within(screen.getByRole("table")).getByRole("link", { name: label("Past Teacher") })).toBeInTheDocument();
  });
});

describe("historical instructor displays", () => {
  it("links every named history row, including after expanding the list", async () => {
    const ranking = section("12345", "Jane Doe", 0.8);
    const view = toSectionView(ranking);
    view.history = Array.from({ length: 9 }, (_, index) => historyRow(`Past Teacher ${index}`, 0.6, 100));
    render(<InstructorHistory view={view} courseCode="ENC 1101" />);
    expect(screen.getAllByRole("link")).toHaveLength(8);
    await userEvent.click(screen.getByRole("button", { name: "Show all 9 instructors" }));
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(9);
    for (const [index, link] of links.entries()) {
      expect(link).toHaveAccessibleName(label(`Past Teacher ${index}`));
      expect(link.previousElementSibling).toHaveTextContent(`Past Teacher ${index}`);
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
    }
  });

  it("omits Staff, blank and unavailable historical names", () => {
    const view = toSectionView(section("12345", null, null));
    view.history = ["Staff", "", "Unavailable", "Jane Doe / John Smith", "José D’Ávila"].map((name) => historyRow(name, 0.6, 100));
    render(<InstructorHistory view={view} courseCode="ENC 1101" />);
    const link = screen.getByRole("link", { name: label("José D’Ávila") });
    expect(screen.getAllByRole("link")).toHaveLength(1);
    expect(link).toHaveAttribute("href", "https://www.ratemyprofessors.com/search/professors/1262?q=Jos%C3%A9%20D%E2%80%99%C3%81vila");
  });
});
