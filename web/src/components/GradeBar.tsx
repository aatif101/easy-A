import { formatShare, type GradeShares } from "../lib/section";

const SEGMENTS = [
  { key: "a", label: "A", className: "bg-green" },
  { key: "b", label: "B", className: "bg-sea" },
  { key: "c", label: "C", className: "bg-silver" },
  { key: "d", label: "D", className: "bg-mist" },
  { key: "f", label: "F", className: "bg-slate" },
] as const;

/** All five letter grades when they are known, otherwise the A share against everything else. */
export function GradeBar({ share, grades = null, faded = false }: { share: number; grades?: GradeShares | null; faded?: boolean }) {
  const percent = Math.round(share * 100);
  const label = grades
    ? SEGMENTS.map(({ key, label: letter }) => `${formatShare(grades[key])} ${letter}`).join(", ")
    : `${formatShare(share)} A, ${100 - percent}% other grades`;
  return (
    <div
      role="img"
      aria-label={label}
      className={`flex h-2 gap-px overflow-hidden rounded-sm ${faded ? "opacity-50" : ""}`}
    >
      {grades ? (
        SEGMENTS.map(({ key, className }) => (
          <div key={key} className={className} style={{ width: `${grades[key] * 100}%` }} />
        ))
      ) : (
        <>
          <div className="bg-green" style={{ width: `${percent}%` }} />
          <div className="flex-1 bg-silver" />
        </>
      )}
    </div>
  );
}

/** The numbers that sit under a bar. D and F stay in the bar; the row names A, B and C. */
export function GradeNumbers({ share, grades = null, full = false }: { share: number; grades?: GradeShares | null; full?: boolean }) {
  return (
    <span className="tabular whitespace-nowrap text-[13px]">
      <strong className="font-bold">A {formatShare(share)}</strong>
      {grades ? ` · B ${formatShare(grades.b)} · C ${formatShare(grades.c)}` : ""}
      {grades && full ? ` · D ${formatShare(grades.d)} · F ${formatShare(grades.f)}` : ""}
    </span>
  );
}

export function GradeLegend() {
  return (
    <span aria-hidden="true" className="inline-flex gap-2 text-xs font-normal">
      {SEGMENTS.map(({ key, label, className }) => (
        <span key={key} className="inline-flex items-center gap-1">
          <span className={`h-2 w-2 ${className}`} />
          {label}
        </span>
      ))}
    </span>
  );
}
