import { useEffect, useId, useRef, useState, type ReactNode } from "react";

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

/** The compact Gen Ed menu beside the search field; picking an area opens its section list. */
function GenEdMenu({ navigate }: HomePageProps) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const popoverId = useId();

  useEffect(() => {
    if (!open) return;
    popoverRef.current?.querySelector<HTMLAnchorElement>("a")?.focus();
    const dismissOutside = (event: MouseEvent) => {
      if (event.target instanceof Node && !buttonRef.current?.contains(event.target) && !popoverRef.current?.contains(event.target)) {
        setOpen(false);
      }
    };
    const dismissWithEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", dismissOutside);
    document.addEventListener("keydown", dismissWithEscape);
    return () => {
      document.removeEventListener("mousedown", dismissOutside);
      document.removeEventListener("keydown", dismissWithEscape);
    };
  }, [open]);

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        aria-label="GenEd filters"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? popoverId : undefined}
        onClick={() => setOpen((value) => !value)}
        className="h-[52px] w-10 shrink-0 rounded-lg border border-silver bg-white text-xl text-ink hover:bg-wash"
      >
        <span aria-hidden="true">⋮</span>
      </button>
      {open ? (
        <div
          ref={popoverRef}
          id={popoverId}
          role="dialog"
          aria-label="GenEd filters"
          className="absolute right-0 top-[60px] z-20 flex max-h-[60vh] w-64 max-w-full flex-col gap-2 overflow-y-auto rounded-lg border border-line bg-white p-3 shadow-lg"
        >
          {GEN_ED_AREAS.map((area) => (
            <a
              key={area.id}
              href={`?gened=${area.id}`}
              onClick={inAppClick(navigate, { view: "gened", area: area.id })}
              className="rounded-lg border border-silver bg-white px-3 py-2 text-sm font-medium text-ink no-underline hover:bg-wash hover:text-ink"
            >
              {area.label}
            </a>
          ))}
        </div>
      ) : null}
    </>
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
        <div className="relative">
          <SearchBox
            inputRef={searchInput}
            placeholder="pre calc"
            onSearch={(q) => navigate({ view: "search", q })}
            rightButton={<GenEdMenu navigate={navigate} />}
          />
        </div>
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
