import type { SectionRanking } from "../types/rankings";
import { signalLabel } from "../utils/rankings";

export function SignalChips({ ranking, compact = true }: { ranking: SectionRanking; compact?: boolean }) {
  if (ranking.signals.length === 0) {
    return <span className="text-sm text-stone-500">Unavailable</span>;
  }
  const visibleSignals = compact ? ranking.signals.slice(0, 2) : ranking.signals;
  const historical = ranking.signal_provenance.freshness === "historical";
  return (
    <div className="flex flex-wrap gap-1.5">
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
      {historical ? (
        <span className="rounded bg-amber-800 px-2 py-0.5 text-xs font-bold text-white">
          Historical only
        </span>
      ) : null}
    </div>
  );
}
