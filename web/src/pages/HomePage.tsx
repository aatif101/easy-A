import { useRef, type ReactNode } from "react";

import { SearchBox } from "../components/SearchBox";
import { inAppClick, type Route } from "../lib/route";
import { GEN_ED_AREAS } from "../lib/search";

interface HomePageProps {
  navigate: (route: Route) => void;
}

const GUIDE: Route = { view: "guide" };

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

/** Three starting points: a known class, a Gen Ed area, or a professor. */
export function HomePage({ navigate }: HomePageProps) {
  const searchInput = useRef<HTMLInputElement>(null);

  return (
    <div className="flex max-w-3xl flex-col gap-4">
      <div className="pb-2">
        <h1 className="text-[28px] font-bold leading-tight tracking-[-0.01em]" style={{ textWrap: "balance" }}>
          See the grades before you register.
        </h1>
        <p className="mt-2 text-slate">How every USF Tampa professor actually graded, from real InfoCenter reports. What do you need?</p>
      </div>

      <Door id="door-class" title="I know which class I need" description="Compare every section and professor for it.">
        <SearchBox inputRef={searchInput} placeholder="e.g. pre calc" onSearch={(q) => navigate({ view: "search", q })} />
        <p className="text-[13px] text-slate">No need to remember the code. Search by class name, course code like ENC 1101, CRN, or professor.</p>
      </Door>

      <div className="grid gap-4 min-[760px]:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Door id="door-gened" title="I just need a GenEd" description="See which sections gave the most A's.">
          <ul className="grid grid-cols-2 gap-2">
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

        <Door
          id="door-professor"
          title="I'm checking a professor"
          description="Type their last name. You'll see their past grades in each course, with a link to their RateMyProfessors page."
        >
          <button
            type="button"
            onClick={() => searchInput.current?.focus()}
            className="inline-flex min-h-11 items-center self-start rounded-lg border border-silver bg-white px-3.5 text-sm font-semibold text-ink hover:bg-wash"
          >
            Search a professor
          </button>
        </Door>
      </div>

      <p className="mt-2 text-[13px] text-slate">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#006747" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="mr-1.5 inline-block align-[-2px]">
          <path d="M5 12l5 5L19 7" />
        </svg>
        Real grades from USF InfoCenter, Fall 2024–Spring 2026.{" "}
        <a href="?guide" onClick={inAppClick(navigate, GUIDE)} className="font-semibold">
          How to read the score
        </a>
      </p>
    </div>
  );
}
