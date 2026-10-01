import type { InstructorBreakdown as InstructorBreakdownData, SectionRanking } from "../types/rankings";
import { formatGradeCount, formatTermCount, formatTermRange } from "../utils/rankings";
import { InfoTip } from "./InfoTip";

const HEADING_NAMED = "Instructors for this course";
const SOURCE_LINE =
  'Source: USF InfoCenter grade reports, matched to instructors in the USF class schedule. "% A" is the share of A–F grades that were an A.';
const CO_TEACHING_CAVEAT =
  "USF lists one instructor per section; co-taught courses are attributed to the listed instructor.";

interface InstructorBreakdownProps {
  ranking: SectionRanking;
  breakdown: InstructorBreakdownData;
  id: string;
}

export function InstructorBreakdown({ breakdown, id }: InstructorBreakdownProps) {
  const headingId = `${id}-instructors-heading`;
  return (
    <section className="mt-6" aria-labelledby={headingId}>
      <div className="flex items-center justify-between gap-2">
        <h4 className="detail-heading" id={headingId}>{HEADING_NAMED}</h4>
        <InfoTip label={CO_TEACHING_CAVEAT} />
      </div>
      <p className="mt-2 text-xs leading-normal text-stone-600">{SOURCE_LINE}</p>
      <ul className="mt-4 space-y-2">
        {breakdown.instructors.map((row) => (
          <li
            className={`rounded-md border p-3 md:flex md:items-start md:justify-between md:gap-4 ${
              row.is_current ? "border-l-4 border-spruce/40 border-l-spruce bg-moss/70" : "border-rule bg-white/70"
            }`}
            key={row.name}
          >
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="break-words text-sm font-bold text-ink">{row.name}</span>
                {row.is_current ? <span className="text-xs font-bold text-spruce">This section</span> : null}
              </div>
              <p className="mt-1 text-sm leading-normal text-stone-700 tabular-nums">
                <span>{Math.round(row.a_share * 100)}% A<span className="sr-only"> grades</span></span>
                <span aria-hidden="true"> · </span>
                <span>{formatGradeCount(row.effective_n)}</span>
                <span aria-hidden="true"> · </span>
                <span>{formatTermCount(row.term_count)} ({formatTermRange(row.first_term, row.last_term)})</span>
              </p>
            </div>
            {row.scored && row.easiness_score !== null ? (
              <div className="mt-3 md:mt-0 md:shrink-0 md:text-right">
                <p className="text-xs leading-normal text-stone-600">Easiness</p>
                <p className="tabular-nums">
                  <span className="font-display text-lg font-bold leading-tight text-spruce">{row.easiness_score.toFixed(1)}</span>
                  <span className="text-xs text-stone-600"> / 10</span>
                </p>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
