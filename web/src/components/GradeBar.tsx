import { formatShare } from "../lib/section";

/** A share against every other A–F grade. The API reports the A share only, so this is two parts. */
export function GradeBar({ share, faded = false }: { share: number; faded?: boolean }) {
  const percent = Math.round(share * 100);
  return (
    <div
      role="img"
      aria-label={`${formatShare(share)} A, ${100 - percent}% other grades`}
      className={`flex h-2 gap-px overflow-hidden rounded-sm ${faded ? "opacity-50" : ""}`}
    >
      <div className="bg-green" style={{ width: `${percent}%` }} />
      <div className="flex-1 bg-silver" />
    </div>
  );
}

export function GradeLegend() {
  return (
    <span aria-hidden="true" className="inline-flex gap-2 text-xs font-normal">
      <span className="inline-flex items-center gap-1">
        <span className="h-2 w-2 bg-green" />A
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="h-2 w-2 bg-silver" />B–F
      </span>
    </span>
  );
}
