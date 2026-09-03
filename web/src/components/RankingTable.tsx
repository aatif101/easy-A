import { Fragment } from "react";

import type { SectionRanking } from "../types/rankings";
import { formatPercent, instructorLabel } from "../utils/rankings";
import { ConfidenceBadge, SeatBadge } from "./Badges";
import { InfoTip } from "./InfoTip";
import { RankingDetails } from "./RankingDetails";
import { SignalChips } from "./SignalChips";

const easinessHelp = "Based on historical grade outcomes and withdrawal rates. Not a guarantee of course difficulty.";
const confidenceHelp = "Confidence reflects the amount and breadth of historical data available.";

interface RankingTableProps {
  rankings: SectionRanking[];
  rankOffset: number;
  expandedCrn: string | null;
  onToggle: (crn: string) => void;
}

export function RankingTable({ rankings, rankOffset, expandedCrn, onToggle }: RankingTableProps) {
  return (
    <>
      <div className="hidden overflow-hidden rounded-lg border border-rule bg-white shadow-ledger lg:block">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1180px] border-collapse text-left">
            <caption className="sr-only">Ranked USF course sections</caption>
            <thead className="bg-ink text-xs uppercase tracking-[0.08em] text-white">
              <tr>
                <th scope="col">Course</th>
                <th scope="col">Section / CRN</th>
                <th scope="col">Instructor</th>
                <th scope="col">Easiness <InfoTip label={easinessHelp} /></th>
                <th scope="col">W rate</th>
                <th scope="col">Confidence <InfoTip label={confidenceHelp} /></th>
                <th scope="col">Seats</th>
                <th scope="col">Modality</th>
                <th scope="col">GenEd</th>
                <th scope="col">Signals</th>
              </tr>
            </thead>
            <tbody>
              {rankings.map((ranking, index) => {
                const expanded = ranking.crn === expandedCrn;
                const detailsId = `details-${ranking.crn}`;
                return (
                  <Fragment key={ranking.crn}>
                    <tr className="ranking-row">
                      <td>
                        <button
                          type="button"
                          className="group text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-spruce"
                          aria-expanded={expanded}
                          aria-controls={detailsId}
                          onClick={() => onToggle(ranking.crn)}
                        >
                          <span className="block font-mono text-[11px] font-bold text-stone-400">#{String(rankOffset + index + 1).padStart(2, "0")}</span>
                          <span className="block font-display text-lg font-bold text-ink underline-offset-4 group-hover:underline">{ranking.subject} {ranking.course_number}</span>
                          <span className="block max-w-52 break-words text-xs leading-snug text-stone-500">{ranking.course_title}</span>
                        </button>
                      </td>
                      <td><span className="text-sm font-semibold text-stone-500">Section unavailable</span><span className="block font-mono text-xs text-stone-500">CRN {ranking.crn}</span></td>
                      <td className="max-w-48 break-words font-semibold">{instructorLabel(ranking)}</td>
                      <td><strong className={`font-display text-xl ${ranking.confidence_label === "low" ? "text-stone-700" : "text-spruce"}`}>{ranking.easiness_score.toFixed(1)}</strong><span className="text-xs text-stone-500"> / 10</span></td>
                      <td className="font-mono text-sm">{formatPercent(ranking.smoothed_withdrawal_rate)}</td>
                      <td><ConfidenceBadge value={ranking.confidence_label} />{ranking.confidence_label === "low" ? <span className="mt-1 flex items-center text-[11px] font-semibold text-amber-800">Low confidence <InfoTip label="Based on limited historical data." /></span> : null}</td>
                      <td><SeatBadge ranking={ranking} /></td>
                      <td className="max-w-36 text-sm">{ranking.modality.delivery_label ?? "Unknown"}</td>
                      <td className="max-w-60">{ranking.gened_attributes.length ? <ul className="space-y-1">{ranking.gened_attributes.map((item) => <li className="break-words text-xs text-stone-600" key={`${item.code}:${item.label}`}><strong className="font-mono text-spruce">{item.code}</strong> · {item.label}</li>)}</ul> : <span className="text-sm text-stone-500">Unavailable</span>}</td>
                      <td className="max-w-64"><SignalChips ranking={ranking} /></td>
                    </tr>
                    {expanded ? (
                      <tr className="bg-paper/70">
                        <td colSpan={10} className="!p-0"><RankingDetails ranking={ranking} id={detailsId} /></td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid gap-3 lg:hidden" aria-label="Course ranking cards">
        {rankings.map((ranking, index) => {
          const expanded = ranking.crn === expandedCrn;
          const detailsId = `mobile-details-${ranking.crn}`;
          return (
            <article className="rounded-lg border border-rule bg-white shadow-ledger" key={ranking.crn}>
              <button className="w-full p-4 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-spruce" type="button" aria-expanded={expanded} aria-controls={detailsId} onClick={() => onToggle(ranking.crn)}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0"><span className="font-mono text-[11px] font-bold text-stone-400">#{String(rankOffset + index + 1).padStart(2, "0")} · CRN {ranking.crn}</span><h2 className="mt-1 break-words font-display text-xl font-bold text-ink">{ranking.subject} {ranking.course_number}</h2><p className="break-words text-sm text-stone-600">{ranking.course_title}</p><p className="mt-1 break-words text-sm font-semibold text-stone-700">{instructorLabel(ranking)}</p></div>
                  <div className="shrink-0 text-right"><strong className={`font-display text-2xl ${ranking.confidence_label === "low" ? "text-stone-700" : "text-spruce"}`}>{ranking.easiness_score.toFixed(1)}</strong><span className="block text-[11px] uppercase tracking-wide text-stone-500">Easiness / 10</span></div>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-2"><SeatBadge ranking={ranking} /><ConfidenceBadge value={ranking.confidence_label} /><span className="text-xs text-stone-500">{ranking.modality.delivery_label ?? "Unknown"}</span></div>
                {ranking.confidence_label === "low" ? <p className="mt-2 text-xs font-semibold text-amber-900">Low confidence · Based on limited historical data.</p> : null}
                <div className="mt-3"><SignalChips ranking={ranking} /></div>
                <span className="mt-4 block border-t border-rule pt-3 text-xs font-bold uppercase tracking-wide text-spruce">{expanded ? "Hide details" : "View details"}</span>
              </button>
              {expanded ? <RankingDetails ranking={ranking} id={detailsId} /> : null}
            </article>
          );
        })}
      </div>
    </>
  );
}
