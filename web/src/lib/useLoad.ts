import { useEffect, useState } from "react";

export type LoadState<Data> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: Data };

/** Runs an abortable request whenever `key` changes; `retry` re-runs it. */
export function useLoad<Data>(
  key: string | null,
  run: (signal: AbortSignal) => Promise<Data>,
): [LoadState<Data>, () => void] {
  const [state, setState] = useState<LoadState<Data>>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (key === null) return;
    const controller = new AbortController();
    setState({ status: "loading" });
    run(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ status: "ready", data });
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          status: "error",
          message: reason instanceof Error ? reason.message : "Request failed.",
        });
      });
    return () => controller.abort();
    // `run` is recreated every render; `key` captures everything it depends on.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, attempt]);

  return [state, () => setAttempt((value) => value + 1)];
}
