import type { SectionRanking } from "../types/rankings";
import { signalLabel, signalSourceLabel } from "../utils/rankings";

export function SignalChips({ ranking, compact = true }: { ranking: SectionRanking; compact?: boolean }) {
  if (ranking.signals.length === 0) {
    return <span className="text-sm text-stone-500">Unavailable</span>;
  }
  const visibleSignals = compact ? ranking.signals.slice(0, 2) : ranking.signals;
  const historical = ranking.signal_provenance.freshness === "historical";
  return (
    <div className="flex flex-wrap gap-1.5">
      <span className={`rounded border px-2 py-0.5 text-xs font-bold ${historical ? "border-amber-400 bg-amber-100 text-amber-950" : "border-stone-300 bg-stone-100 text-stone-700"}`}>
        {signalSourceLabel(ranking)}
      </span>
      {visibleSignals.map((signal) => (
        <span
          className={`rounded border px-2 py-0.5 text-xs font-semibold ${
            historical
              ? "border-amber-300 bg-amber-50 text-amber-950"
              : "border-spruce/20 bg-moss/60 text-spruce"
          }`}
          key={`${signal.signal_type}:${signal.value}`}
        >
          {signalLabel(signal)}
        </span>
      ))}
      {compact && ranking.signals.length > 2 ? (
        <span className="px-1 py-0.5 text-xs font-semibold text-stone-500">
          +{ranking.signals.length - 2}
        </span>
      ) : null}
    </div>
  );
}
