import { useEffect, useState } from "react";
import type { CourseCoverage, CoverageLoader } from "../types/rankings";

interface CoverageNoticeProps {
  term: string;
  subject?: string;
  courseNumber?: string;
  loader: CoverageLoader;
}

/** Mounted with a term key so coverage from another term is never displayed. */
export function CoverageNotice({ term, subject, courseNumber, loader }: CoverageNoticeProps) {
  const [items, setItems] = useState<CourseCoverage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(false);
    loader(term, controller.signal)
      .then((result) => { if (!controller.signal.aborted) setItems(result); })
      .catch(() => { if (!controller.signal.aborted) { setItems([]); setError(true); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [term, loader, version]);

  if (loading) return <p role="status" className="mb-4 text-xs text-stone-600">Loading beta coverage information...</p>;
  if (error) return (
    <aside className="mb-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950" role="status">
      <p>Coverage information unavailable. You can still search sections.</p>
      <button type="button" className="mt-2 font-bold underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2" onClick={() => setVersion((current) => current + 1)}>Retry coverage</button>
    </aside>
  );
  const course = items.find((item) => item.subject === subject && item.course_number === courseNumber);
  // An absent target says nothing about arbitrary course availability.
  const message = course && !course.catalog_present
    ? "Catalog information is not currently available for this configured course."
    : course?.status === "missing" && course.section_count === 0
      ? "No current sections have been observed for this configured course."
      : null;
  return message ? <p className="mb-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950" role="status">{subject} {courseNumber}: {message}</p> : null;
}
