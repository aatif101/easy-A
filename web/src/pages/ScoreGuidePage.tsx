import type { ReactNode } from "react";

import { GradeLegend } from "../components/GradeBar";
import { inAppClick, type Route } from "../lib/route";

function Item({ title, sample, children }: { title: string; sample: ReactNode; children: ReactNode }) {
  return (
    <li className="grid gap-x-5 gap-y-1.5 border-t border-line py-4 first:border-t-0 min-[640px]:grid-cols-[180px_minmax(0,1fr)]">
      <div className="flex items-start">{sample}</div>
      <div>
        <h2 className="font-semibold">{title}</h2>
        <div className="text-slate">{children}</div>
      </div>
    </li>
  );
}

const Caption = ({ children, warn = false }: { children: ReactNode; warn?: boolean }) => (
  <span className={`tabular text-xs ${warn ? "text-warn" : "text-slate"}`}>{children}</span>
);

/** What each part of a section row means. Explains the labels only; shows no course data. */
export function ScoreGuidePage({ navigate }: { navigate: (route: Route) => void }) {
  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold leading-tight">How to read the score</h1>
      <p className="mt-2 text-slate">
        Every section shows how the professor teaching it graded the same course in past semesters, from USF InfoCenter grade
        reports (Fall 2024–Spring 2026).
      </p>

      <ol className="mt-6 flex flex-col">
        <Item title="The score (A%)" sample={<span className="text-lg font-bold">A%</span>}>
          The share of A–F grades this professor gave in this course that were an A. Higher means more A's in their past classes.
          A dash (—) means there is no A rate to show.
        </Item>
        <Item title="The grade bar" sample={<GradeLegend />}>
          Green is the A share; gray is every other letter grade, B through F. A faded bar means the number rests on too few
          grades to trust.
        </Item>
        <Item title="Grades and terms" sample={<Caption>N grades · T terms</Caption>}>
          How much history the A% is based on. More grades over more terms make it more reliable.
        </Item>
        <Item title="When there is no score" sample={<Caption warn>No history for this instructor here</Caption>}>
          <ul className="mt-1 flex list-disc flex-col gap-1 pl-5">
            <li><strong className="font-medium text-ink">Too few to trust:</strong> the professor has some grades in this course, but not enough to rank.</li>
            <li><strong className="font-medium text-ink">No history for this instructor here:</strong> they have no recorded grades for this course.</li>
            <li><strong className="font-medium text-ink">Instructor not announced yet:</strong> USF lists the section as TBA or Staff.</li>
            <li><strong className="font-medium text-ink">No grade history for this course:</strong> no past grades are recorded for it at all.</li>
            <li><strong className="font-medium text-ink">Lab section, no letter grades:</strong> labs don't give A–F grades.</li>
          </ul>
        </Item>
        <Item title="Compare instructors" sample={<span className="rounded-md border border-silver px-2.5 py-1 text-xs font-semibold">Compare instructors</span>}>
          Opens everyone who has taught the course recently, with their own A rates, so you can see who else teaches it.
        </Item>
        <Item title="RMP" sample={<span className="text-xs font-medium text-slate underline underline-offset-2">RMP ↗</span>}>
          Opens the professor's RateMyProfessors page (or a search for their name there) in a new tab, so you can read reviews too.
        </Item>
        <Item title="Copy CRN" sample={<span className="rounded-md border border-silver px-2 py-1 text-xs font-semibold">Copy</span>}>
          Copies the section's CRN. Paste it into OASIS to register. Seat counts can lag, so confirm seats in OASIS.
        </Item>
      </ol>

      <p className="mt-4 rounded-lg bg-wash px-4 py-3 text-sm text-slate">
        Past grades describe past classes, not yours. Use them to compare sections, not to predict your grade.
      </p>
      <a href={window.location.pathname} onClick={inAppClick(navigate, { view: "home" })} className="mt-4 inline-block text-sm font-semibold">
        Back to search
      </a>
    </div>
  );
}
