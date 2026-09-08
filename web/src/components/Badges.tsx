import { formatAbsoluteTime, formatRelativeTime, UNAVAILABLE_TIME } from "../utils/time";
import type { ConfidenceLabel, SeatFreshness, SectionRanking } from "../types/rankings";

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

const freshnessLabels: Record<SeatFreshness, string> = {
  fresh: "Fresh", aging: "Aging", stale: "Stale", unavailable: "Unavailable",
};
const freshnessStyles: Record<SeatFreshness, string> = {
  fresh: "text-emerald-900", aging: "text-amber-900", stale: "text-red-900", unavailable: "text-stone-600",
};

export function SeatBadge({ ranking }: { ranking: SectionRanking }) {
  const seats = ranking.seats;
  const remaining = seats.seats_remaining;
  const relative = formatRelativeTime(seats.observed_at);
  const absolute = formatAbsoluteTime(seats.observed_at);
  const count = remaining === null ? "Seat availability unavailable"
    : remaining < 0 ? `Over-enrolled by ${Math.abs(remaining)} (${remaining} seats remaining)`
    : remaining === 0 ? "Full - 0 seats open" : `${remaining} seats open`;
  return (
    <span className="block space-y-1 text-xs text-stone-700">
      <span className="block font-semibold">Latest observed seats</span>
      <span className="block font-bold">{count}</span>
      <span className={`block font-bold ${freshnessStyles[seats.freshness]}`}>{freshnessLabels[seats.freshness]}</span>
      {relative === UNAVAILABLE_TIME ? <span className="block">Observation time unavailable</span> : (
        <time className="block" dateTime={seats.observed_at ?? undefined} title={absolute}>
          {seats.freshness === "stale" ? "Last checked" : "Updated"} {relative}
        </time>
      )}
      {seats.freshness === "stale" ? <span className="block">Stale observation; availability may have changed.</span> : null}
      {seats.wait_seats_available !== null ? <span className="block">Waitlist: {seats.wait_seats_available} spots available</span> : null}
    </span>
  );
}
