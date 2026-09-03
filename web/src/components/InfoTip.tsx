interface InfoTipProps {
  label: string;
}

export function InfoTip({ label }: InfoTipProps) {
  return (
    <span className="group relative inline-flex align-middle">
      <button
        type="button"
        className="ml-1 inline-grid size-5 place-items-center rounded-full border border-spruce/30 text-[11px] font-bold text-spruce transition hover:bg-moss focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-spruce"
        aria-label={label}
      >
        i
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full right-0 z-30 mb-2 w-64 translate-y-1 rounded-md bg-ink px-3 py-2 text-left text-xs font-normal leading-relaxed text-white opacity-0 shadow-xl transition group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:translate-y-0 group-focus-within:opacity-100"
      >
        {label}
      </span>
    </span>
  );
}
