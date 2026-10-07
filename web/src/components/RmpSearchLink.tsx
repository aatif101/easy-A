import { rmpSearchUrl } from "../lib/rmp";

export function RmpSearchLink({ instructor }: { instructor: string | null | undefined }) {
  const href = rmpSearchUrl(instructor);
  if (!href) return null;
  const label = `Search for ${instructor?.trim()} on Rate My Professors`;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      title={`${label} (opens in a new tab)`}
      className="inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded px-1 text-xs font-medium text-slate underline underline-offset-2 hover:bg-wash hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-green"
    >
      RMP <span aria-hidden="true" className="ml-1">↗</span>
    </a>
  );
}
