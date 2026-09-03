import type { ConfidenceLabel, SectionRanking } from "../types/rankings";

const confidenceStyles: Record<ConfidenceLabel, string> = {
  low: "border-amber-300 bg-amber-50 text-amber-900",
  medium: "border-blue-200 bg-blue-50 text-blue-900",
  high: "border-emerald-200 bg-emerald-50 text-emerald-900",
};

export function ConfidenceBadge({ value }: { value: ConfidenceLabel }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-bold capitalize ${confidenceStyles[value]}`}
    >
      {value}
    </span>
  );
}

export function SeatBadge({ ranking }: { ranking: SectionRanking }) {
  const seats = ranking.seats_remaining;
  if (seats === null) {
    return <span className="text-sm font-semibold text-stone-500">Unknown</span>;
  }
  if (seats <= 0) {
    return (
      <span className="inline-flex rounded-full border border-stone-300 bg-stone-100 px-2 py-0.5 text-xs font-bold text-stone-700">
        Full · 0
      </span>
    );
  }
  return (
    <span className="inline-flex rounded-full border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-900">
      Open · {seats}
    </span>
  );
}
