import { useEffect, useState } from "react";
import type { SyncStatus as SyncStatusData, SyncStatusLoader } from "../types/rankings";
import { formatAbsoluteTime, formatRelativeTime } from "../utils/time";

interface SyncStatusProps {
  term: string;
  loader: SyncStatusLoader;
  /** Mock/demo mode: seat freshness is not live and no "Updated" time may be shown. */
  synthetic?: boolean;
}

const AMBER_PANEL = "mb-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950";

/** Mounted with a term key so freshness from another term is never displayed. */
export function SyncStatus({ term, loader, synthetic = false }: SyncStatusProps) {
  const [status, setStatus] = useState<SyncStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (synthetic) return;
    const controller = new AbortController();
    setLoading(true);
    setError(false);
    loader(term, controller.signal)
      .then((result) => { if (!controller.signal.aborted) setStatus(result); })
      .catch(() => { if (!controller.signal.aborted) { setStatus(null); setError(true); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [term, loader, version, synthetic]);

  if (synthetic) return <p className="mb-4 text-xs text-stone-600">Synthetic demo data: seat freshness is not live.</p>;
  if (loading) return <p className="mb-4 text-xs text-stone-600">Checking data freshness…</p>;
  if (error || !status) return (
    <aside className={AMBER_PANEL} role="status">
      <p>Data freshness unavailable.</p>
      <button type="button" className="mt-2 font-bold underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2" onClick={() => setVersion((current) => current + 1)}>Retry freshness</button>
    </aside>
  );
  if (status.last_success_at === null) return <p className={AMBER_PANEL} role="status">Seat data has not been verified by the live sync yet.</p>;
  return (
    <div className="mb-4">
      <p className="text-xs text-stone-600" title={formatAbsoluteTime(status.last_success_at)}>Updated {formatRelativeTime(status.last_success_at)}</p>
      {status.is_stale ? <p className={`mt-2 ${AMBER_PANEL.replace("mb-4 ", "")}`} role="status">Seat data may be out of date.</p> : null}
    </div>
  );
}
