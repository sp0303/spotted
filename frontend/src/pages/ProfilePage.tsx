import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError, type BusinessProfile, type Fact, type Service } from "../api";
import { FactList } from "../components/FactList";
import { LocationsEditor } from "../components/LocationsEditor";
import { OriginBadge } from "../components/OriginBadge";

const fact = (value: string): Fact => ({ value, origin: "confirmed" });
const service = (value: string): Service => ({ value, origin: "confirmed" });

/** Client-side version of the API's confirm rules, so the owner sees problems before submitting. */
export function confirmProblems(p: BusinessProfile): string[] {
  const out: string[] = [];
  if (!p.name.value.trim()) out.push("Add your business name.");
  const noCountry = p.locations.filter((l) => !l.country_code || l.country_code.length !== 2);
  if (noCountry.length) out.push(`Add a two-letter country code for ${noCountry.length} location(s), e.g. US.`);
  if (!p.locations.some((l) => l.is_target)) out.push("Add at least one place where you want customers to find you.");
  return out;
}

function SingleFact({
  label,
  value,
  onChange,
  multiline,
}: {
  label: string;
  value: Fact | null | undefined;
  onChange: (f: Fact | null) => void;
  multiline?: boolean;
}) {
  const text = value?.value ?? "";
  const set = (v: string) => onChange(v ? { ...(value ?? fact(v)), value: v, origin: "confirmed" } : null);
  return (
    <label className="single-fact">
      <span className="label-row">
        {label}
        {value && <OriginBadge origin={value.origin} sourceUrl={value.source_url} evidence={value.evidence} />}
      </span>
      {multiline ? (
        <textarea rows={3} value={text} onChange={(e) => set(e.target.value)} />
      ) : (
        <input value={text} onChange={(e) => set(e.target.value)} />
      )}
    </label>
  );
}

export default function ProfilePage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [tried, setTried] = useState(false);

  useEffect(() => {
    api
      .getProfile(id)
      .then((s) => {
        setProfile(s.profile);
        setConfirmed(s.confirmed);
      })
      .catch((e) => setLoadError(e instanceof ApiError ? e.message : "Couldn't load this profile."));
  }, [id]);

  if (loadError)
    return (
      <p className="error" role="alert">
        {loadError} <Link to="/">Start again</Link>
      </p>
    );
  if (!profile) return <p role="status">Loading…</p>;

  const set = <K extends keyof BusinessProfile>(key: K, value: BusinessProfile[K]) =>
    setProfile({ ...profile, [key]: value });
  const problems = confirmProblems(profile);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setTried(true);
    if (!profile || confirmProblems(profile).length) return;
    setSaving(true);
    setSaveError(null);
    try {
      // Drop rows the owner left empty.
      const clean = (xs: Fact[]) => xs.filter((x) => x.value.trim());
      const body: BusinessProfile = {
        ...profile,
        aliases: clean(profile.aliases),
        subcategories: clean(profile.subcategories),
        services: profile.services.filter((x) => x.value.trim()),
        phones: clean(profile.phones),
        emails: clean(profile.emails),
        hours: clean(profile.hours),
        languages: clean(profile.languages),
        differentiators: clean(profile.differentiators),
        suggested_competitors: clean(profile.suggested_competitors),
      };
      await api.confirmProfile(id, body);
      navigate(`/b/${id}/checks`);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Couldn't save. Please try again.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="profile" noValidate>
      <div className="page-head">
        <p className="eyebrow">Step 1 of 2 · Check your profile</p>
        <h1>{profile.name.value || "Your business"}</h1>
        <p className="muted">
          <a href={profile.website_url} target="_blank" rel="noreferrer noopener">
            {profile.domain}
          </a>
          {confirmed && " · confirmed"}
        </p>
        <p>
          This is what we found on your website. Everything we test is based on it, so please correct anything
          that's wrong. <span className="legend-inline">
            <OriginBadge origin="extracted" /> your website says it · <OriginBadge origin="inferred" /> we guessed,
            please check · <OriginBadge origin="confirmed" /> you entered it
          </span>
        </p>
      </div>

      {profile.warnings.length > 0 && (
        <aside className="callout" aria-label="Things to check">
          <h2>Please check</h2>
          <ul>
            {profile.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </aside>
      )}

      <section className="card">
        <h2>The basics</h2>
        <SingleFact label="Business name" value={profile.name} onChange={(f) => set("name", f ?? fact(""))} />
        <SingleFact label="What kind of business is it?" value={profile.category} onChange={(f) => set("category", f)} />
        <SingleFact label="Description" value={profile.description} onChange={(f) => set("description", f)} multiline />
        <SingleFact
          label="Who are your customers?"
          value={profile.target_customer}
          onChange={(f) => set("target_customer", f)}
        />
        <FactList
          label="Other names you go by"
          hint="Used to spot you in AI answers, e.g. a shorter name."
          items={profile.aliases}
          onChange={(v) => set("aliases", v)}
          make={fact}
        />
      </section>

      <section className="card">
        <h2>Where do you want to be found?</h2>
        <p className="hint">
          We only test the places you confirm here. We never assume a service area your website doesn't name.
        </p>
        <LocationsEditor items={profile.locations} onChange={(v) => set("locations", v)} />
      </section>

      <section className="card">
        <h2>What you offer</h2>
        <FactList label="Products and services" items={profile.services} onChange={(v) => set("services", v)} make={service} />
        <FactList
          label="What makes you different"
          items={profile.differentiators}
          onChange={(v) => set("differentiators", v)}
          make={fact}
        />
        <FactList label="Other categories" items={profile.subcategories} onChange={(v) => set("subcategories", v)} make={fact} />
      </section>

      <section className="card">
        <h2>Contact details</h2>
        <div className="two-col">
          <FactList label="Phone numbers" items={profile.phones} onChange={(v) => set("phones", v)} make={fact} />
          <FactList label="Email addresses" items={profile.emails} onChange={(v) => set("emails", v)} make={fact} />
          <FactList label="Opening hours" items={profile.hours} onChange={(v) => set("hours", v)} make={fact} />
          <FactList
            label="Languages"
            hint="Two-letter codes, e.g. en, es."
            items={profile.languages}
            onChange={(v) => set("languages", v)}
            make={fact}
          />
        </div>
        {profile.social_profiles.length > 0 && (
          <fieldset className="fact-list">
            <legend>Profiles linked from your site</legend>
            <ul>
              {profile.social_profiles.map((s, i) => (
                <li key={s.url} className="fact-row">
                  <span className="pill pill-cap">{s.platform.replaceAll("_", " ")}</span>
                  <a href={s.url} target="_blank" rel="noreferrer noopener" className="truncate">
                    {s.url}
                  </a>
                  <button
                    type="button"
                    className="icon-btn"
                    aria-label={`Remove ${s.url}`}
                    onClick={() => set("social_profiles", profile.social_profiles.filter((_, j) => j !== i))}
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          </fieldset>
        )}
      </section>

      <section className="card">
        <h2>Competitors</h2>
        <FactList
          label="Businesses you compete with"
          hint="Our suggestions come from AI knowledge and may be out of date. We'll also add the ones AI assistants name."
          items={profile.suggested_competitors}
          onChange={(v) => set("suggested_competitors", v)}
          make={fact}
        />
      </section>

      <details className="pages-read">
        <summary>Pages we read ({profile.pages_read.length})</summary>
        <ul>
          {profile.pages_read.map((u) => (
            <li key={u}>
              <a href={u} target="_blank" rel="noreferrer noopener">
                {u}
              </a>
            </li>
          ))}
        </ul>
      </details>

      <div className="sticky-actions">
        {tried && problems.length > 0 && (
          <ul className="error" role="alert">
            {problems.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        )}
        {saveError && (
          <p className="error" role="alert">
            {saveError}
          </p>
        )}
        <button type="submit" className="primary" disabled={saving}>
          {saving ? "Saving…" : "Confirm and check my website"}
        </button>
      </div>
    </form>
  );
}
