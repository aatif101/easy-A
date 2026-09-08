interface EmptyRankingsProps {
  filtered: boolean;
  termLabel: string;
  onReset: () => void;
}

/** Search results alone cannot establish whether a course is covered by the beta. */
export function EmptyRankings({ filtered, termLabel, onReset }: EmptyRankingsProps) {
  return (
    <section className="rounded-lg border border-dashed border-stone-400 bg-white/60 p-10 text-center" role="status">
      <h2 className="font-display text-2xl font-bold">{filtered ? "No sections are currently available for this search" : `No sections available for ${termLabel}`}</h2>
      <p className="mt-2 text-sm text-stone-600">{filtered ? "Try clearing or widening filters. Beta coverage may be incomplete; this result does not establish whether a course is offered." : "This term is listed by the API but has no searchable section data."}</p>
      {filtered ? <button type="button" className="mt-5 rounded-md bg-spruce px-4 py-2 text-sm font-bold text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-spruce" onClick={onReset}>Reset filters</button> : null}
    </section>
  );
}
