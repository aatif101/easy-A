import { useEffect, useId, useRef, useState } from "react";

import { inAppClick, type Route } from "../lib/route";
import { GEN_ED_AREAS } from "../lib/search";

interface GenEdMenuProps {
  navigate: (route: Route) => void;
  size?: "large" | "compact";
  /** The Gen Ed area on screen now, if any. */
  current?: string;
}

/**
 * The ⋮ button beside a search field; picking an area opens its section list. Place it inside a
 * `relative` wrapper around the search box so the menu lines up under the field.
 */
export function GenEdMenu({ navigate, size = "large", current }: GenEdMenuProps) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const popoverId = useId();

  useEffect(() => {
    if (!open) return;
    const links = popoverRef.current?.querySelectorAll<HTMLAnchorElement>("a");
    (popoverRef.current?.querySelector<HTMLAnchorElement>('[aria-current="page"]') ?? links?.[0])?.focus();
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

  const large = size === "large";
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
        className={`${large ? "h-[52px]" : "h-11"} w-10 shrink-0 rounded-lg border border-silver bg-white text-xl text-ink hover:bg-wash`}
      >
        <span aria-hidden="true">⋮</span>
      </button>
      {open ? (
        <div
          ref={popoverRef}
          id={popoverId}
          role="dialog"
          aria-label="GenEd filters"
          className={`absolute right-0 ${large ? "top-[60px]" : "top-[52px]"} z-20 flex max-h-[60vh] w-64 max-w-full flex-col gap-2 overflow-y-auto rounded-lg border border-line bg-white p-3 shadow-lg`}
        >
          {GEN_ED_AREAS.map((area) => (
            <a
              key={area.id}
              href={`?gened=${area.id}`}
              aria-current={area.id === current ? "page" : undefined}
              onClick={(event) => {
                setOpen(false);
                inAppClick(navigate, { view: "gened", area: area.id })(event);
              }}
              className={`rounded-lg border px-3 py-2 text-sm font-medium no-underline ${
                area.id === current ? "border-ink bg-ink text-white hover:text-white" : "border-silver bg-white text-ink hover:bg-wash hover:text-ink"
              }`}
            >
              {area.label}
            </a>
          ))}
        </div>
      ) : null}
    </>
  );
}
