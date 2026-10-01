import type {
  InstructorBreakdown as InstructorBreakdownData,
  InstructorHistoryRow,
  SectionRanking,
} from "../types/rankings";
import { formatGradeCount, formatTermCount, formatTermRange, isNamedInstructor } from "../utils/rankings";
import { InfoTip } from "./InfoTip";

const HEADING_NAMED = "Instructors for this course";
const HEADING_STAFF = "Historically taught by";
const SOURCE_LINE =
  'Source: USF InfoCenter grade reports, matched to instructors in the USF class schedule. "% A" is the share of A–F grades that were an A.';
const STAFF_EXPLAINER =
  "This section's instructor is not yet named. These instructors taught this course in past terms. They do not affect this section's score.";
const CO_TEACHING_CAVEAT =
  "USF lists one instructor per section; co-taught courses are attributed to the listed instructor.";
const LAB_NOTE = "Instructor history is not shown for lab sections. The figures above are course-wide.";
const EMPTY_NOTE =
  "No instructor-level grade history is recorded for this course. Course-wide history above still applies.";
const NO_HISTORY_LINE = "No recorded grade history for this instructor in this course.";
const COURSE_WIDE_LINE = "This section's score uses course-wide history.";
const USED_IN_SCORE = "Used in this section's score";
const NOT_USED_IN_SCORE = "Not used in this section's score.";

/** Maximum rows visible before the native disclosure, pinned row included (UI-SPEC). */
const VISIBLE_ROW_CAP = 5;

const DASHED_NOTE = "rounded-md border border-dashed border-stone-300 bg-white/50 p-4 text-sm font-bold text-stone-600";
const CHIP = "rounded border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-950";
const ROW_BASE = "rounded-md border p-3 md:flex md:items-start md:justify-between md:gap-4";
const ROW_PLAIN = `${ROW_BASE} border-rule bg-white/70`;
const ROW_PINNED = `${ROW_BASE} border-l-4 border-spruce/40 border-l-spruce bg-moss/70`;

interface InstructorBreakdownProps {
  ranking: SectionRanking;
  breakdown: InstructorBreakdownData;
  id: string;
}

interface RowProps {
  row: InstructorHistoryRow;
  pinned: boolean;
  usedInScore: boolean;
  scoringMin: number;
}

function InstructorRow({ row, pinned, usedInScore, scoringMin }: RowProps) {
  const scored = row.scored && row.easiness_score !== null;
  return (
    <li className={pinned ? ROW_PINNED : ROW_PLAIN}>
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="break-words text-sm font-bold text-ink">{row.name}</span>
          {row.term_count === 1 ? <span className={CHIP}>Based on 1 term</span> : null}
          {!scored ? <span className={CHIP}>Limited sample</span> : null}
          {pinned ? <span className="text-xs font-bold text-spruce">This section</span> : null}
        </div>
        <p className="mt-1 text-sm leading-normal text-stone-700 tabular-nums">
          <span>{Math.round(row.a_share * 100)}% A<span className="sr-only"> grades</span></span>
          <span aria-hidden="true"> · </span>
          <span>{formatGradeCount(row.effective_n)}</span>
          <span aria-hidden="true"> · </span>
          <span>{formatTermCount(row.term_count)} ({formatTermRange(row.first_term, row.last_term)})</span>
        </p>
      </div>
      <div className="mt-3 md:mt-0 md:shrink-0 md:text-right">
        {scored && row.easiness_score !== null ? (
          <>
            <p className="text-xs leading-normal text-stone-600">Easiness</p>
            <p className="tabular-nums">
              <span className="font-display text-lg font-bold leading-tight text-spruce">{row.easiness_score.toFixed(1)}</span>
              <span className="text-xs text-stone-600"> / 10</span>
            </p>
            {pinned && usedInScore ? (
              <p className="mt-1 text-xs font-bold leading-normal text-spruce">{USED_IN_SCORE}</p>
            ) : null}
          </>
        ) : (
          <>
            <p className="text-sm font-bold text-stone-700">Not scored</p>
            <p className="text-xs leading-normal text-stone-600">Under {Math.round(scoringMin)} grades</p>
            {pinned ? (
              <p className="mt-1 text-xs leading-normal text-stone-600">
                {NOT_USED_IN_SCORE} {COURSE_WIDE_LINE}
              </p>
            ) : null}
          </>
        )}
      </div>
    </li>
  );
}

function NoHistoryPinnedRow({ name }: { name: string }) {
  return (
    <li className={ROW_PINNED}>
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="break-words text-sm font-bold text-ink">{name}</span>
          <span className="text-xs font-bold text-spruce">This section</span>
        </div>
        <p className="mt-1 text-sm leading-normal text-stone-700">{NO_HISTORY_LINE}</p>
        <p className="mt-1 text-xs leading-normal text-stone-600">{COURSE_WIDE_LINE}</p>
      </div>
    </li>
  );
}

export function InstructorBreakdown({ ranking, breakdown, id }: InstructorBreakdownProps) {
  // Lab sections show only the dashed note: no heading, no tip, no rows (D-13).
  if (breakdown.status === "lab_section") {
    return (
      <section className="mt-6" aria-label="Instructor history">
        <p className={DASHED_NOTE}>{LAB_NOTE}</p>
      </section>
    );
  }

  const headingId = `${id}-instructors-heading`;
  // A pinned row exists only for a real named person (D-10, D-11).
  const named = isNamedInstructor(ranking) && Boolean(breakdown.current_instructor);

  // API order is current first, then n desc, then name asc. Defensively move the
  // is_current row first, and drop duplicates so the pinned row appears once.
  const pinnedRow = named && breakdown.current_instructor_has_history
    ? breakdown.instructors.find((row) => row.is_current) ?? null
    : null;
  const otherRows = breakdown.instructors.filter((row) => !(named && row.is_current));
  const noHistoryName = named && !pinnedRow ? breakdown.current_instructor : null;

  const pinnedCount = pinnedRow || noHistoryName ? 1 : 0;
  const visibleOthers = otherRows.slice(0, VISIBLE_ROW_CAP - pinnedCount);
  const hiddenOthers = otherRows.slice(VISIBLE_ROW_CAP - pinnedCount);

  const isEmpty = !named && breakdown.instructors.length === 0;
  const usedInScore = ranking.score_source === "instructor_course";
  const othersCount = Math.round(breakdown.other_instructor_count);
  const cutoff = Math.round(breakdown.collapse_min_effective_n);

  const renderRow = (row: InstructorHistoryRow) => (
    <InstructorRow
      key={row.name}
      row={row}
      pinned={false}
      usedInScore={usedInScore}
      scoringMin={breakdown.scoring_min_effective_n}
    />
  );

  return (
    <section className="mt-6" aria-labelledby={headingId}>
      <div className="flex items-center justify-between gap-2">
        <h4 className="detail-heading" id={headingId}>{named ? HEADING_NAMED : HEADING_STAFF}</h4>
        <InfoTip label={CO_TEACHING_CAVEAT} />
      </div>

      {isEmpty ? (
        <p className={`mt-4 ${DASHED_NOTE}`}>{EMPTY_NOTE}</p>
      ) : (
        <>
          <p className="mt-2 text-xs leading-normal text-stone-600">{SOURCE_LINE}</p>
          {!named ? <p className="mt-2 text-xs leading-normal text-stone-600">{STAFF_EXPLAINER}</p> : null}
          <ul className="mt-4 space-y-2">
            {pinnedRow ? (
              <InstructorRow
                key={pinnedRow.name}
                row={pinnedRow}
                pinned
                usedInScore={usedInScore}
                scoringMin={breakdown.scoring_min_effective_n}
              />
            ) : null}
            {noHistoryName ? <NoHistoryPinnedRow name={noHistoryName} /> : null}
            {visibleOthers.map(renderRow)}
          </ul>
          {hiddenOthers.length > 0 ? (
            <details className="mt-2">
              <summary className="min-h-11 cursor-pointer py-3 text-sm font-bold text-spruce focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-spruce">
                Show all {breakdown.instructors.length} instructors
              </summary>
              <ul className="mt-2 space-y-2">{hiddenOthers.map(renderRow)}</ul>
            </details>
          ) : null}
        </>
      )}

      {othersCount > 0 ? (
        <p className="mt-2 text-xs leading-normal text-stone-600">
          {othersCount === 1
            ? `1 other instructor with under ${cutoff} grades`
            : `${othersCount} other instructors with under ${cutoff} grades each`}
        </p>
      ) : null}
    </section>
  );
}
