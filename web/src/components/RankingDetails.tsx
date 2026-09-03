import type { SectionRanking } from "../types/rankings";
import {
  formatPercent,
  scoreSourceLabel,
  signalLabel,
  signalSourceLabel,
} from "../utils/rankings";
import { ConfidenceBadge, SeatBadge } from "./Badges";

export function RankingDetails({ ranking, id }: { ranking: SectionRanking; id: string }) {
  const signalSource = signalSourceLabel(ranking);
  const historicalSignals = ranking.signal_provenance.freshness === "historical";

  return (
    <section id={id} aria-label={`Details for ${ranking.subject} ${ranking.course_number} CRN ${ranking.crn}`} className="detail-panel">
      <div className="flex flex-col gap-2 border-b border-rule pb-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="eyebrow">{ranking.subject} {ranking.course_number} · CRN {ranking.crn}</p>
          <h3 className="mt-1 font-display text-2xl font-bold text-ink">{ranking.course_title}</h3>
          <p className="mt-1 text-sm text-stone-600">{ranking.instructor ?? "Staff"} · {ranking.modality.delivery_label ?? "Unknown modality"}</p>
        </div>
        {historicalSignals ? (
          <span className="w-fit rounded-sm border border-amber-400 bg-amber-50 px-3 py-1 text-xs font-extrabold uppercase tracking-wide text-amber-950">
            Historical reference
          </span>
        ) : null}
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-5 md:grid-cols-4">
        <div><dt>Easiness</dt><dd>{ranking.easiness_score.toFixed(1)} / 10</dd></div>
        <div><dt>W rate</dt><dd>{formatPercent(ranking.smoothed_withdrawal_rate)}</dd></div>
        <div><dt>Effective sample</dt><dd>{Math.round(ranking.effective_n)} grades</dd></div>
        <div><dt>Confidence</dt><dd><ConfidenceBadge value={ranking.confidence_label} /></dd></div>
        <div><dt>Score source</dt><dd>{scoreSourceLabel(ranking.score_source)}</dd></div>
        <div><dt>Seats</dt><dd><SeatBadge ranking={ranking} /></dd></div>
        <div><dt>Enrollment</dt><dd>{ranking.seats.enrollment ?? "Unknown"} / {ranking.seats.capacity ?? "Unknown"}</dd></div>
        <div><dt>Waitlist seats</dt><dd>{ranking.seats.wait_seats_available ?? "Unknown"}</dd></div>
      </dl>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="detail-heading">Policy signals</h4>
            <span className={`source-label ${historicalSignals ? "source-label-historical" : ""}`}>{signalSource}</span>
          </div>
          {ranking.signals.length ? (
            <ul className="mt-3 space-y-3">
              {ranking.signals.map((signal) => (
                <li className="rounded-md border border-rule bg-white/70 p-3" key={`${signal.signal_type}:${signal.value}`}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-sm font-bold text-ink">{signalLabel(signal)}</span>
                    <span className="font-mono text-[11px] text-stone-500">{Math.round(signal.confidence * 100)}% rule confidence</span>
                  </div>
                  <p className="mt-2 border-l-2 border-brass/60 pl-3 text-sm leading-relaxed text-stone-700">“{signal.evidence}”</p>
                  {signal.freshness === "historical" ? (
                    <p className="mt-2 text-xs font-semibold text-amber-900">Historical syllabus reference · {signal.source_term}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 rounded-md border border-dashed border-stone-300 bg-white/50 p-4 text-sm font-semibold text-stone-600">No policy information available</p>
          )}
        </div>

        <div>
          <h4 className="detail-heading">General Education</h4>
          {ranking.gened_attributes.length ? (
            <ul className="mt-3 space-y-2">
              {ranking.gened_attributes.map((attribute) => (
                <li className="rounded-md bg-moss/70 px-3 py-2 text-sm text-spruce" key={attribute.code}>
                  <strong className="font-mono text-xs">{attribute.code}</strong>
                  <span className="ml-2">{attribute.label}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-stone-500">Unavailable</p>
          )}
          <p className="mt-5 text-xs leading-relaxed text-stone-500">Historical analytics cover {ranking.historical_analytics.term_count} term{ranking.historical_analytics.term_count === 1 ? "" : "s"} and {ranking.historical_analytics.section_count} section{ranking.historical_analytics.section_count === 1 ? "" : "s"}. Scores are historical estimates, not guarantees.</p>
        </div>
      </div>
    </section>
  );
}
