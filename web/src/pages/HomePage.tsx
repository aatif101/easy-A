import type { ReactNode } from "react";

import { CoursePreview } from "../components/CoursePreview";
import { GenEdMenu } from "../components/GenEdMenu";
import { SearchBox } from "../components/SearchBox";
import { inAppClick, type Route } from "../lib/route";
import { GEN_ED_AREAS } from "../lib/search";
import type { RankingLoader } from "../types/rankings";

interface HomePageProps {
  term: string;
  rankingLoader: RankingLoader;
  navigate: (route: Route) => void;
}

function Door({ id, title, description, children }: { id: string; title: string; description: string; children?: ReactNode }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3 rounded-xl border border-silver px-3.5 py-[18px] sm:px-5">
      <div>
        <h2 id={id} className="text-lg font-bold">{title}</h2>
        <p className="text-sm text-slate">{description}</p>
      </div>
      {children}
    </section>
  );
}

/** Search first, then a live example of a familiar course, then Gen Ed browsing. */
export function HomePage({ term, rankingLoader, navigate }: HomePageProps) {
  return (
    <div className="flex max-w-3xl flex-col gap-4">
      <div className="pb-2">
        <h1 className="text-[28px] font-bold leading-tight tracking-[-0.01em]" style={{ textWrap: "balance" }}>
          See the grades before you register.
        </h1>
        <p className="mt-2 text-slate">How every USF Tampa professor actually graded, from real InfoCenter reports.</p>
      </div>

      <Door id="door-class" title="I know which class I need" description="Compare every section and professor for it.">
        <div className="relative">
          <SearchBox
            placeholder="pre calc"
            onSearch={(q) => navigate({ view: "search", q })}
            rightButton={<GenEdMenu navigate={navigate} />}
          />
        </div>
        <div className="flex flex-col gap-1 text-[13px] text-slate">
          <p>No need to remember the code. Search by class name, course code like ENC 1101, or CRN.</p>
          <p>Checking a professor? Type their last name.</p>
        </div>
      </Door>

      <CoursePreview term={term} rankingLoader={rankingLoader} navigate={navigate} />

      <Door id="door-gened" title="I just need a GenEd" description="See which sections gave the most A's.">
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {GEN_ED_AREAS.map((area) => (
            <li key={area.id}>
              <a
                href={`?gened=${area.id}`}
                onClick={inAppClick(navigate, { view: "gened", area: area.id })}
                className="flex min-h-[52px] items-center justify-between gap-2 rounded-lg bg-wash px-3 text-sm font-semibold text-ink no-underline hover:bg-line hover:text-ink"
              >
                {area.label}
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#466069" strokeWidth="2" strokeLinecap="round" aria-hidden="true" className="shrink-0">
                  <path d="M9 6l6 6-6 6" />
                </svg>
              </a>
            </li>
          ))}
        </ul>
      </Door>

      <p className="mt-2 text-[13px] text-slate">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#006747" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="mr-1.5 inline-block align-[-2px]">
          <path d="M5 12l5 5L19 7" />
        </svg>
        Real grades from USF InfoCenter, Fall 2024–Spring 2026.
      </p>
    </div>
  );
}
