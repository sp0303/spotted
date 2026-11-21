import { useId } from "react";
import type { Fact } from "../api";
import { OriginBadge } from "./OriginBadge";

/** Editable list of values, each with its origin. Editing a value makes it the owner's. */
export function FactList<T extends Fact>({
  label,
  hint,
  items,
  onChange,
  placeholder,
  make,
}: {
  label: string;
  hint?: string;
  items: T[];
  onChange: (items: T[]) => void;
  placeholder?: string;
  make: (value: string) => T;
}) {
  const id = useId();
  const update = (i: number, value: string) =>
    onChange(items.map((it, j) => (j === i ? { ...it, value, origin: "confirmed" } : it)));
  return (
    <fieldset className="fact-list">
      <legend>{label}</legend>
      {hint && <p className="hint">{hint}</p>}
      {items.length === 0 && <p className="empty">None yet.</p>}
      <ul>
        {items.map((item, i) => (
          <li key={i} className="fact-row">
            <input
              aria-label={`${label} ${i + 1}`}
              id={`${id}-${i}`}
              value={item.value}
              placeholder={placeholder}
              onChange={(e) => update(i, e.target.value)}
            />
            <OriginBadge origin={item.origin} sourceUrl={item.source_url} evidence={item.evidence} />
            <button
              type="button"
              className="icon-btn"
              aria-label={`Remove ${item.value || "item"}`}
              onClick={() => onChange(items.filter((_, j) => j !== i))}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
      <button type="button" className="link-btn" onClick={() => onChange([...items, make("")])}>
        + Add
      </button>
    </fieldset>
  );
}
