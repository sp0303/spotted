import type { Location } from "../api";
import { OriginBadge } from "./OriginBadge";

const FIELDS: { key: keyof Location; label: string; width?: string }[] = [
  { key: "label", label: "Name (optional)" },
  { key: "address", label: "Street address" },
  { key: "city", label: "City" },
  { key: "region", label: "State / region" },
  { key: "postal_code", label: "Postcode", width: "short" },
  { key: "country_code", label: "Country (2 letters)", width: "short" },
];

export function newLocation(): Location {
  return { is_physical: false, is_target: true, priority: 1, origin: "confirmed" };
}

/** Physical locations and service areas: where the owner wants customers to find them. */
export function LocationsEditor({ items, onChange }: { items: Location[]; onChange: (items: Location[]) => void }) {
  const set = (i: number, patch: Partial<Location>) =>
    onChange(items.map((loc, j) => (j === i ? { ...loc, ...patch, origin: "confirmed" } : loc)));
  return (
    <div className="locations">
      {items.length === 0 && <p className="empty">No locations yet. Add where you want customers to find you.</p>}
      {items.map((loc, i) => {
        const title = loc.label || [loc.city, loc.region].filter(Boolean).join(", ") || "New location";
        return (
          <fieldset key={i} className={`location-card${loc.is_target ? "" : " is-muted"}`}>
            <legend>
              {title} <OriginBadge origin={loc.origin} sourceUrl={loc.source_url} evidence={loc.evidence} />
            </legend>
            <div className="segmented" role="radiogroup" aria-label={`Type of ${title}`}>
              <label>
                <input type="radio" checked={loc.is_physical} onChange={() => set(i, { is_physical: true })} />
                Customers can visit
              </label>
              <label>
                <input type="radio" checked={!loc.is_physical} onChange={() => set(i, { is_physical: false })} />
                Service area
              </label>
            </div>
            <div className="grid">
              {FIELDS.filter((f) => loc.is_physical || f.key !== "address").map((f) => (
                <label key={f.key} className={f.width === "short" ? "short" : ""}>
                  <span>{f.label}</span>
                  <input
                    value={(loc[f.key] as string | null | undefined) ?? ""}
                    maxLength={f.key === "country_code" ? 2 : undefined}
                    required={f.key === "country_code"}
                    aria-invalid={f.key === "country_code" && !loc.country_code ? true : undefined}
                    onChange={(e) =>
                      set(i, {
                        [f.key]: f.key === "country_code" ? e.target.value.toUpperCase() : e.target.value || null,
                      })
                    }
                  />
                </label>
              ))}
            </div>
            <div className="location-foot">
              <label className="checkbox">
                <input type="checkbox" checked={loc.is_target} onChange={(e) => set(i, { is_target: e.target.checked })} />
                I want customers here to find me
              </label>
              <button type="button" className="link-btn danger" onClick={() => onChange(items.filter((_, j) => j !== i))}>
                Remove
              </button>
            </div>
          </fieldset>
        );
      })}
      <button type="button" className="link-btn" onClick={() => onChange([...items, newLocation()])}>
        + Add a location or service area
      </button>
    </div>
  );
}
