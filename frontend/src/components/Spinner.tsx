import { useEffect, useState } from "react";

/** Progress with plain-language steps that advance on a timer (the request itself is one call). */
export function Working({ steps, intervalMs = 4000 }: { steps: string[]; intervalMs?: number }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((n) => Math.min(n + 1, steps.length - 1)), intervalMs);
    return () => clearInterval(t);
  }, [steps.length, intervalMs]);
  return (
    <div className="working" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <ol>
        {steps.map((s, j) => (
          <li key={s} className={j < i ? "done" : j === i ? "current" : ""}>
            {s}
          </li>
        ))}
      </ol>
    </div>
  );
}
