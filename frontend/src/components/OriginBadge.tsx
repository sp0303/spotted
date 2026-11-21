import type { Origin } from "../api";

const LABELS: Record<Origin, string> = {
  extracted: "From your site",
  inferred: "Our guess",
  confirmed: "Confirmed",
};

const HINTS: Record<Origin, string> = {
  extracted: "Your website says this.",
  inferred: "We worked this out ourselves. Please check it.",
  confirmed: "You confirmed or entered this.",
};

/** Shows where a value came from; for website facts, the page and the quote. */
export function OriginBadge({
  origin,
  sourceUrl,
  evidence,
}: {
  origin: Origin;
  sourceUrl?: string | null;
  evidence?: string | null;
}) {
  const title = [HINTS[origin], evidence ? `“${evidence}”` : "", sourceUrl ?? ""].filter(Boolean).join("\n");
  const badge = (
    <span className={`badge badge-${origin}`} title={title}>
      {LABELS[origin]}
    </span>
  );
  if (origin === "extracted" && sourceUrl) {
    return (
      <a className="badge-link" href={sourceUrl} target="_blank" rel="noreferrer noopener" title={title}>
        {badge}
      </a>
    );
  }
  return badge;
}
