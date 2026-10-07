import type { ReactNode } from "react";

export function Loading({ label }: { label: string }) {
  return (
    <p role="status" className="py-8 text-sm text-slate">
      {label}
    </p>
  );
}

export function LoadError({ onRetry, message = "Unable to load sections. Check your connection and try again." }: { onRetry: () => void; message?: string }) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-lg border border-line px-4 py-4 text-sm">
      <span>{message}</span>
      <button type="button" onClick={onRetry} className="h-9 rounded-md border border-silver px-3 font-semibold hover:bg-wash">
        Try again
      </button>
    </div>
  );
}

export function Notice({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-line px-4 py-5">
      <p className="font-semibold">{title}</p>
      <div className="mt-1 text-sm text-slate">{children}</div>
    </div>
  );
}
