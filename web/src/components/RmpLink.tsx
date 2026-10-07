import { rmpLink } from "../lib/rmp";

export function RmpLink({ instructor, subject }: { instructor: string | null | undefined; subject: string }) {
  const link = rmpLink(instructor, subject);
  if (!link) return null;
  const name = instructor?.trim();
  const label =
    link.kind === "profile"
      ? `Rate My Professors profile for ${name}`
      : `Search for ${name} on Rate My Professors`;
  return (
    <a
      href={link.href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      title={`${label} (opens in a new tab)`}
      className="inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded px-1 text-xs font-medium text-slate underline underline-offset-2 hover:bg-wash hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-green sm:min-h-0 sm:min-w-0"
    >
      RMP <span aria-hidden="true" className="ml-1">↗</span>
    </a>
  );
}
