import { useEffect, useState } from "react";
import type { SyncStatus as SyncStatusData, SyncStatusLoader } from "../types/rankings";
import { formatAbsoluteTime, formatRelativeTime } from "../utils/time";

interface SyncStatusProps {
  term: string;
  loader: SyncStatusLoader;
  /** Mock/demo mode: seat freshness is not live and no "Updated" time may be shown. */
  synthetic?: boolean;
}

const RENDER_TICK_MS = 30_000;
const REFETCH_MS = 300_000;

const AMBER_PANEL = "mb-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950";

/** Mounted with a term key so freshness from another term is never displayed. */
export function SyncStatus({ term, loader, synthetic = false }: SyncStatusProps) {
  const [status, setStatus] = useState<SyncStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (synthetic) return;
    const controller = new AbortController();
    loader(term, controller.signal)
      .then((result) => { if (!controller.signal.aborted) { setStatus(result); setNow(Date.now()); } })
      // A failed refresh keeps the last known status; with none, the unavailable notice shows.
      .catch(() => undefined)
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [term, loader, version, synthetic]);

  useEffect(() => {
    if (synthetic) return;
    // Re-render so the relative time and the staleness check keep moving on a long-open page.
    const tick = setInterval(() => setNow(Date.now()), RENDER_TICK_MS);
    // Refetch keeps the previous status on screen; only the very first load shows the loading text.
    const refetch = setInterval(() => setVersion((current) => current + 1), REFETCH_MS);
    return () => { clearInterval(tick); clearInterval(refetch); };
  }, [synthetic]);

  const retry = () => { setLoading(true); setVersion((current) => current + 1); };

  if (synthetic) return <p className="mb-4 text-xs text-stone-600">Synthetic demo data: seat freshness is not live.</p>;
  if (loading) return <p className="mb-4 text-xs text-stone-600">Checking data freshness…</p>;
  if (!status) return (
    <aside className={AMBER_PANEL} role="status">
      <p>Data freshness unavailable.</p>
      <button type="button" className="mt-2 font-bold underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2" onClick={retry}>Retry freshness</button>
    </aside>
  );
  if (status.last_success_at === null) return <p className={AMBER_PANEL} role="status">Seat data has not been verified by the live sync yet.</p>;
  // The API owns the threshold; the browser only compares elapsed time with stale_after_seconds.
  const succeededAt = Date.parse(status.last_success_at);
  const outdated = status.is_stale || (Number.isFinite(succeededAt) && now - succeededAt > status.stale_after_seconds * 1000);
  return (
    <div className="mb-4">
      <p className="text-xs text-stone-600" title={formatAbsoluteTime(status.last_success_at)}>Updated {formatRelativeTime(status.last_success_at, now)}</p>
      {outdated ? <p className={`mt-2 ${AMBER_PANEL.replace("mb-4 ", "")}`} role="status">Seat data may be out of date.</p> : null}
    </div>
  );
}
