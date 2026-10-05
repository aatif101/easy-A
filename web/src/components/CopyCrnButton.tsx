import { useEffect, useState } from "react";

const copyText = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
};

/** Students paste CRNs straight into OASIS registration. */
export function CopyCrnButton({ crn, large = false }: { crn: string; large?: boolean }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");

  useEffect(() => {
    if (state === "idle") return;
    const timer = window.setTimeout(() => setState("idle"), 2000);
    return () => window.clearTimeout(timer);
  }, [state]);

  const label = state === "copied" ? "Copied" : state === "failed" ? "Copy failed" : large ? "Copy CRN" : "Copy";
  return (
    <button
      type="button"
      aria-label={state === "idle" ? `Copy CRN ${crn}` : `${label}: CRN ${crn}`}
      onClick={() => {
        void copyText(crn).then((ok) => setState(ok ? "copied" : "failed"));
      }}
      className={`whitespace-nowrap rounded-md border border-silver bg-white font-semibold text-ink hover:bg-wash ${
        large ? "h-10 px-3.5 text-sm" : "h-7 px-2 text-xs"
      }`}
    >
      {label}
    </button>
  );
}
