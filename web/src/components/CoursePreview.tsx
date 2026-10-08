import { useState } from "react";

import { loadAllSections } from "../lib/loadAll";
import { inAppClick, type Route } from "../lib/route";
import { toSectionView, type SectionView } from "../lib/section";
import { useLoad } from "../lib/useLoad";
import type { RankingLoader, SectionRanking } from "../types/rankings";
import { Marker, SectionCard } from "./SectionCard";
import { LoadError, Loading, Notice } from "./Status";

/** Courses most first-year students take, so the example is one they recognize. */
const PREVIEW_COURSES = [
  { subject: "ENC", number: "1101" },
  { subject: "MAC", number: "1147" },
  { subject: "PSY", number: "2012" },
  { subject: "AMH", number: "2020" },
] as const;

const SHOWN = 3;
const TIPS_KEY = "easy-a:hide-reading-tips";

const readTipsHidden = (): boolean => {
  try {
    return window.localStorage.getItem(TIPS_KEY) === "1";
  } catch {
    return false;
  }
};

const writeTipsHidden = (hidden: boolean) => {
  try {
    if (hidden) window.localStorage.setItem(TIPS_KEY, "1");
    else window.localStorage.removeItem(TIPS_KEY);
  } catch {
    // Storage can be blocked; the tips then simply show again next visit.
  }
};

/** The highest-A sections whose own instructor has enough history, one per instructor. */
const topSections = (items: SectionRanking[]) => {
  const rows: { ranking: SectionRanking; view: SectionView }[] = [];
  for (const ranking of items) {
    const view = toSectionView(ranking);
    if (view.kind !== "instructor" || rows.some((row) => row.view.instructor === view.instructor)) continue;
    rows.push({ ranking, view });
  }
  return rows.sort((left, right) => (right.view.aShare ?? 0) - (left.view.aShare ?? 0)).slice(0, SHOWN);
};

function ReadingKey({ onHide }: { onHide: () => void }) {
  const items = [
    ["A rate.", "Of the A–F grades this professor gave in this course in past semesters, the share that were an A."],
    ["How much data.", "The grades and terms behind the A rate. More of both means a number you can trust more."],
    ["Their RMP.", "Opens their RateMyProfessors page, so you can read the reviews too."],
    ["Register.", "Copy the CRN and paste it into OASIS."],
  ];
  return (
    <div className="mt-1 flex flex-col gap-3 border-t border-line pt-3 text-sm">
      <ol aria-label="How to read this card" className="flex flex-col gap-2">
        {items.map(([title, text], index) => (
          <li key={title} className="grid grid-cols-[22px_minmax(0,1fr)] gap-2.5">
            <Marker n={index + 1} />
            <span>
              <strong className="font-semibold">{title}</strong> <span className="text-slate">{text}</span>
            </span>
          </li>
        ))}
      </ol>
      <button type="button" onClick={onHide} className="self-start text-[13px] font-semibold text-green underline-offset-2 hover:underline">
        Hide tips
      </button>
    </div>
  );
}

interface CoursePreviewProps {
  term: string;
  rankingLoader: RankingLoader;
  navigate: (route: Route) => void;
}

/** A live example on the home page: real sections of a familiar course, with a reading key. */
export function CoursePreview({ term, rankingLoader, navigate }: CoursePreviewProps) {
  const [course, setCourse] = useState<(typeof PREVIEW_COURSES)[number]>(PREVIEW_COURSES[0]);
  const [tipsHidden, setTipsHidden] = useState(readTipsHidden);
  const [open, setOpen] = useState<string | null>(null);
  const code = `${course.subject} ${course.number}`;
  const [state, retry] = useLoad(`${term}:${course.subject}:${course.number}`, (signal) =>
    loadAllSections(rankingLoader, [{ term, subject: course.subject, course_number: course.number }], signal),
  );
  const rows = state.status === "ready" ? topSections(state.data) : [];
  const allRoute: Route = { view: "search", q: code };
  const setHidden = (hidden: boolean) => {
    setTipsHidden(hidden);
    writeTipsHidden(hidden);
  };

  return (
    <section aria-labelledby="preview-heading" className="flex flex-col gap-3 py-2">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <div>
          <h2 id="preview-heading" className="text-lg font-bold">See it on a class everyone takes</h2>
          <p className="text-sm text-slate">The professors who gave the most A's in past semesters.</p>
        </div>
        {tipsHidden ? (
          <button type="button" onClick={() => setHidden(false)} className="text-[13px] font-semibold text-green underline-offset-2 hover:underline">
            How to read this
          </button>
        ) : null}
      </div>

      <div role="group" aria-label="Example course" className="flex flex-wrap gap-2">
        {PREVIEW_COURSES.map((item) => {
          const label = `${item.subject} ${item.number}`;
          const on = item === course;
          return (
            <button
              key={label}
              type="button"
              aria-pressed={on}
              onClick={() => {
                setCourse(item);
                setOpen(null);
              }}
              className={`h-11 rounded-full border px-4 text-sm font-semibold ${on ? "border-ink bg-ink text-white" : "border-silver bg-white text-ink hover:bg-wash"}`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {state.status === "loading" ? <Loading label={`Loading ${code} sections…`} /> : null}
      {state.status === "error" ? <LoadError onRetry={retry} /> : null}
      {state.status === "ready" && rows.length === 0 ? (
        <Notice title={`No ${code} sections with enough instructor history yet`}>
          <a href={`?q=${encodeURIComponent(code)}`} onClick={inAppClick(navigate, allRoute)}>
            See every {code} section
          </a>
        </Notice>
      ) : null}
      {rows.length > 0 ? (
        <>
          {state.status === "ready" ? <p className="text-sm text-slate">{code} · {state.data[0].course_title}</p> : null}
          <ul className="flex flex-col gap-2.5">
            {rows.map(({ ranking, view }, index) => (
              <SectionCard
                key={ranking.crn}
                ranking={ranking}
                view={view}
                open={open === ranking.crn}
                onToggle={() => setOpen((current) => (current === ranking.crn ? null : ranking.crn))}
                markers={!tipsHidden && index === 0}
              >
                {!tipsHidden && index === 0 ? <ReadingKey onHide={() => setHidden(true)} /> : null}
              </SectionCard>
            ))}
          </ul>
          {state.status === "ready" ? (
            <a href={`?q=${encodeURIComponent(code)}`} onClick={inAppClick(navigate, allRoute)} className="self-start text-sm font-semibold">
              See all {state.data.length} {code} sections
            </a>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
