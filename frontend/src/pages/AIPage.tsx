import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  api,
  ApiError,
  type AIResult,
  type AIRun,
  type AISearchComparison,
  type AISearchSide,
  type AITier,
  type PromptIn,
  type PromptSuggestions,
} from "../api";

const INTENT_LABELS: Record<string, string> = {
  discovery: "Finding a business",
  service: "A service",
  attribute: "Something special",
  budget: "Price",
  problem: "A problem",
  neighborhood: "Nearby",
  comparison: "Comparing",
  branded: "Your name",
  accuracy: "Your details",
  voice_style: "Voice",
};

const SOURCE_LABELS: Record<string, string> = {
  own_site: "Your website",
  competitor_site: "Competitor's site",
  directory: "Directory",
  review_site: "Reviews",
  publication: "Publication",
  blog_listicle: "Blog list",
  forum: "Forum",
  social: "Social",
  maps: "Maps",
  marketplace: "Marketplace",
  other: "Other",
};

const POLL_MS = 1500;
const POLL_FULL_MS = 4000; // a full audit takes minutes and its results are large

const isBranded = (p: { intent: string }) => p.intent === "branded" || p.intent === "accuracy";

/** Consumer apps with no API we can use: links that open the app with the question filled in, for the owner to
 * look at themselves (the "app view"). We never automate these apps. */
const APP_LINKS: { label: string; url: (q: string) => string }[] = [
  { label: "Bing AI Mode", url: (q) => `https://www.bing.com/copilotsearch?q=${encodeURIComponent(q)}` },
  { label: "Google AI Mode", url: (q) => `https://www.google.com/search?udm=50&q=${encodeURIComponent(q)}` },
  { label: "ChatGPT", url: (q) => `https://chatgpt.com/?q=${encodeURIComponent(q)}` },
  { label: "Perplexity", url: (q) => `https://www.perplexity.ai/search?q=${encodeURIComponent(q)}` },
];

function CheckYourself({ question }: { question: string }) {
  return (
    <p className="small check-yourself">
      <span className="muted">Check it yourself: </span>
      {APP_LINKS.map((a, i) => (
        <span key={a.label}>
          {i > 0 && " · "}
          <a href={a.url(question)} target="_blank" rel="noopener noreferrer">
            {a.label}
          </a>
        </span>
      ))}
      <span className="muted"> (opens the app in your browser; answers there can differ from what we measured)</span>
    </p>
  );
}

export default function AIPage() {
  const { id = "" } = useParams();
  const [run, setRun] = useState<AIRun | null>(null);
  const [setup, setSetup] = useState<PromptSuggestions | null>(null);
  const [prompts, setPrompts] = useState<PromptIn[]>([]);
  const [chosen, setChosen] = useState<string[]>([]);
  const [tier, setTier] = useState<AITier>("free");
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadSetup = useCallback(async () => {
    const s = await api.getAIPrompts(id);
    setSetup(s);
    setPrompts(s.prompts);
    setTier("free");
    setChosen(s.platforms.filter((p) => p.default).map((p) => p.key));
  }, [id]);

  const poll = useCallback((auditId: string) => {
    const tick = async () => {
      try {
        const r = await api.getAIRun(auditId);
        setRun(r);
        if (r.status === "running") timer.current = setTimeout(tick, r.tier === "paid" ? POLL_FULL_MS : POLL_MS);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Couldn't load the results.");
      }
    };
    void tick();
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const latest = await api.getLatestAIRun(id);
        if (cancelled) return;
        setRun(latest);
        if (latest.status === "running") poll(latest.audit_id);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 404) {
          try {
            await loadSetup();
            setEditing(true);
          } catch (e2) {
            setError(e2 instanceof ApiError ? e2.message : "Couldn't load your questions.");
          }
        } else setError(e instanceof ApiError ? e.message : "Couldn't load the results.");
      }
    })();
    return () => {
      cancelled = true;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [id, loadSetup, poll]);

  function chooseTier(next: AITier) {
    if (!setup || next === tier) return;
    setTier(next);
    setPrompts(next === "paid" ? (setup.full_prompts ?? setup.prompts) : setup.prompts);
  }

  async function start() {
    setStarting(true);
    setError(null);
    setNotice(null);
    try {
      const { audit_id, reused } = await api.startAIRun(
        id,
        prompts.filter((p) => p.text.trim()),
        chosen,
        tier,
      );
      if (reused)
        setNotice(
          "You asked these same questions less than an hour ago, so here are those answers again instead of a new run.",
        );
      setEditing(false);
      setRun(null);
      if (timer.current) clearTimeout(timer.current);
      poll(audit_id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't start the run.");
    } finally {
      setStarting(false);
    }
  }

  async function newRun() {
    setError(null);
    setNotice(null);
    try {
      if (!setup) await loadSetup();
      setEditing(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't load your questions.");
    }
  }

  return (
    <section className="ai-page">
      <div className="page-head">
        <p className="eyebrow">Step 3 of 4 · What do AI assistants say?</p>
        <h1>Ask the AI assistants</h1>
        <p>
          We ask AI assistants the questions your customers ask, and record whether they name you, who they name
          instead, and which websites they rely on.
        </p>
        <p className="muted">
          <Link to={`/b/${id}/checks`}>← Back to website foundations</Link>
        </p>
      </div>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {notice && !editing && (
        <p className="hint notice" role="status">
          {notice}
        </p>
      )}

      {editing && setup && (
        <PromptEditor
          setup={setup}
          tier={tier}
          onTier={chooseTier}
          prompts={prompts}
          setPrompts={setPrompts}
          chosen={chosen}
          setChosen={setChosen}
          starting={starting}
          onStart={start}
          onCancel={run ? () => setEditing(false) : undefined}
        />
      )}

      {!editing && !run && !error && (
        <div className="working" role="status">
          <span className="spinner" aria-hidden="true" />
          <span>Loading…</span>
        </div>
      )}

      {!editing && run && <Results run={run} onNewRun={newRun} />}
    </section>
  );
}

function PromptEditor(props: {
  setup: PromptSuggestions;
  tier: AITier;
  onTier: (t: AITier) => void;
  prompts: PromptIn[];
  setPrompts: (p: PromptIn[]) => void;
  chosen: string[];
  setChosen: (c: string[]) => void;
  starting: boolean;
  onStart: () => void;
  onCancel?: () => void;
}) {
  const { setup, tier, onTier, prompts, setPrompts, chosen, setChosen, starting, onStart, onCancel } = props;
  const full = setup.full_audit;
  const paid = tier === "paid";
  const filled = prompts.filter((p) => p.text.trim());
  const brandedCount = filled.filter(isBranded).length;
  const coreCount = filled.length - brandedCount;
  const fullPlatforms = full?.platforms.length ?? 0;
  const fullLocations = Math.max(1, full?.locations.length ?? 1);
  const calls = paid
    ? coreCount * (full?.runs ?? 1) * fullLocations * fullPlatforms + brandedCount * fullPlatforms
    : filled.length * chosen.length;
  const maxPrompts = paid && full ? full.max_core + full.max_branded : setup.max_prompts;
  const tooMany = paid && full ? coreCount > full.max_core || brandedCount > full.max_branded : false;

  function edit(i: number, text: string) {
    setPrompts(prompts.map((p, j) => (j === i ? { ...p, text, user_edited: true } : p)));
  }

  return (
    <div className="card">
      <fieldset className="tier-choice">
        <legend>How thorough?</legend>
        <label className={`tier-option ${!paid ? "is-chosen" : ""}`}>
          <input type="radio" name="tier" checked={!paid} onChange={() => onTier("free")} />
          <span>
            <strong>Free run</strong>
            <span className="small muted">
              Up to {setup.max_prompts} questions, asked once each. First answers in about a minute.
            </span>
          </span>
        </label>
        <label className={`tier-option ${paid ? "is-chosen" : ""} ${full?.enabled ? "" : "is-soon"}`}>
          <input
            type="radio"
            name="tier"
            aria-label="Full audit"
            checked={paid}
            disabled={!full?.enabled}
            onChange={() => onTier("paid")}
          />
          <span>
            <strong>Full audit</strong>
            {!full?.enabled && <span className="badge badge-soon">Coming soon</span>}
            <span className="small muted">
              {full
                ? `Up to ${full.max_core} customer questions plus ${full.max_branded} about you, asked ${full.runs} times each` +
                  (full.locations.length > 1 ? ` in each of ${full.locations.join(", ")}` : "") +
                  (full.search_off ? ", with and without web search" : "") +
                  ". Runs in the background (up to an hour)."
                : "More questions, repeat runs, every location, with and without web search."}
            </span>
            {full && full.coming_soon.length > 0 && (
              <span className="small muted">Coming soon in the full audit: {full.coming_soon.join(" · ")}.</span>
            )}
          </span>
        </label>
      </fieldset>

      <h2>Questions your customers might ask</h2>
      <p className="hint">
        We wrote these from your profile. Edit them so they sound like your customers. Questions with your name
        check what AI knows about you; the others check whether it finds you.
      </p>
      <ol className="prompt-list">
        {prompts.map((p, i) => (
          <li key={i} className="fact-row">
            <input
              aria-label={`Question ${i + 1}`}
              value={p.text}
              maxLength={300}
              onChange={(e) => edit(i, e.target.value)}
            />
            <span className="pill">{INTENT_LABELS[p.intent] ?? p.intent}</span>
            <button
              type="button"
              className="icon-btn"
              aria-label={`Remove question ${i + 1}`}
              onClick={() => setPrompts(prompts.filter((_, j) => j !== i))}
            >
              ×
            </button>
          </li>
        ))}
      </ol>
      {prompts.length < maxPrompts && (
        <button
          type="button"
          className="link-btn"
          onClick={() => setPrompts([...prompts, { text: "", intent: "discovery", user_edited: true }])}
        >
          + Add a question
        </button>
      )}

      {paid && full && (
        <p className="hint">
          The full audit asks every assistant that's set up
          {full.search_off ? ", plus Gemini without web search to compare what it remembers with what it finds" : ""}.
          Questions with your name are asked once, in your main city.
        </p>
      )}
      <fieldset className="platforms">
        <legend>AI assistants to ask</legend>
        {setup.platforms.length === 0 && <p className="empty">No AI assistant is set up on the server.</p>}
        {!paid &&
          setup.platforms.map((p) => (
            <label key={p.key} className="checkbox">
              <input
                type="checkbox"
                checked={chosen.includes(p.key)}
                onChange={(e) =>
                  setChosen(e.target.checked ? [...chosen, p.key] : chosen.filter((k) => k !== p.key))
                }
              />
              {p.label}
              {!p.search_enabled && <span className="muted small">(no web search)</span>}
            </label>
          ))}
        {paid &&
          setup.platforms
            .filter((p) => full?.platforms.includes(p.key))
            .map((p) => (
              <label key={p.key} className="checkbox">
                <input type="checkbox" checked readOnly disabled />
                {p.label}
                {!p.search_enabled && <span className="muted small">(no web search)</span>}
              </label>
            ))}
        {setup.coming_soon.map((p) => (
          <label key={p.key} className="checkbox is-soon" title={p.note || undefined}>
            <input type="checkbox" disabled />
            {p.label}
            <span className="badge badge-soon">Coming soon</span>
            {p.note && <span className="muted small">{p.note}</span>}
          </label>
        ))}
      </fieldset>

      <div className="actions-row">
        <button type="button" className="primary" disabled={starting || !calls || tooMany} onClick={onStart}>
          {starting
            ? "Starting…"
            : paid
              ? "Start the full audit"
              : `Ask ${chosen.length} assistant${chosen.length === 1 ? "" : "s"}`}
        </button>
        <span className="muted small">
          {paid
            ? `About ${calls} answers in total. You can leave this page while it runs.`
            : `${calls} question${calls === 1 ? "" : "s"} in total, asked once each, all at the same time.`}
        </span>
        {tooMany && full && (
          <span className="error small">
            Up to {full.max_core} customer questions and {full.max_branded} with your name.
          </span>
        )}
        {onCancel && (
          <button type="button" className="link-btn" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

function Results({ run, onNewRun }: { run: AIRun; onNewRun: () => void }) {
  const running = run.status === "running";
  const city = run.location.city;
  const locations = run.locations ?? [];
  const multiLoc = locations.length > 1;
  const [locId, setLocId] = useState<string | null>(null);
  const shownLoc = multiLoc ? (locId ?? locations[0].id) : null;
  const repeats = (run.runs_per_prompt ?? 1) > 1;
  return (
    <>
      <div className={`run-status ${running ? "is-running" : ""}`} role="status" aria-live="polite">
        {running && <span className="spinner" aria-hidden="true" />}
        <span>
          {running
            ? `Asking… ${run.finished_runs} of ${run.expected_runs} answers in`
            : `${run.finished_runs} answers`}
          {run.first_result_seconds != null && ` · first answer after ${run.first_result_seconds}s`}
          {run.tier === "paid" && ` · full audit, ${run.runs_per_prompt ?? 1} runs per question`}
          {city && !multiLoc && ` · questions asked about ${city}`}
          {multiLoc && ` · ${locations.length} locations`}
          {` · cost $${run.cost_usd.toFixed(3)}`}
        </span>
        {!running && (
          <button type="button" className="link-btn" onClick={onNewRun}>
            Ask again
          </button>
        )}
      </div>
      {run.note && <p className="hint">{run.note}</p>}
      {run.skipped_platforms.map((s) => (
        <p key={s.key} className="hint">
          {s.label} was skipped: {s.reason}
        </p>
      ))}

      <h2 className="section-title">Did they name you?</h2>
      <p className="hint">
        Counted over {run.visibility_answers} answer{run.visibility_answers === 1 ? "" : "s"} to questions that don't
        use your name{repeats ? `, each question asked ${run.runs_per_prompt} times` : ""}. Answers change between
        runs, so treat small numbers as a first look, not a score.
      </p>
      <div className="platform-cards">
        {run.platforms.map((p) => (
          <div key={p.key} className={`stat ${p.named ? "stat-pass" : p.answers ? "stat-issue" : ""}`}>
            <span className="small">{p.label}</span>
            <strong>
              {p.named} <span className="of">of {p.answers}</span>
            </strong>
            <span className="small">
              {p.recommended ? `recommended in ${p.recommended}` : p.answers ? "never recommended" : "no answers yet"}
              {p.best_position != null && ` · best #${p.best_position}`}
              {p.errors > 0 && ` · ${p.errors} failed`}
              {(p.skipped ?? 0) > 0 && ` · ${p.skipped} not run`}
            </span>
          </div>
        ))}
      </div>

      {run.search_comparison && <SearchContrast sc={run.search_comparison} />}

      {multiLoc && (
        <section className="card">
          <h2>By location</h2>
          <div className="platform-cards">
            {locations.map((l) => (
              <div key={l.id} className={`stat ${l.named ? "stat-pass" : l.answers ? "stat-issue" : ""}`}>
                <span className="small">{l.city ?? "Your area"}</span>
                <strong>
                  {l.named} <span className="of">of {l.answers}</span>
                </strong>
                <span className="small">
                  {l.competitors.length
                    ? `most named: ${l.competitors
                        .slice(0, 2)
                        .map((c) => c.name)
                        .join(", ")}`
                    : "no other businesses yet"}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="card">
        <h2>Answers by question</h2>
        {multiLoc && (
          <div className="loc-tabs" role="tablist" aria-label="Location">
            {locations.map((l) => (
              <button
                key={l.id}
                type="button"
                role="tab"
                aria-selected={shownLoc === l.id}
                className={shownLoc === l.id ? "is-active" : ""}
                onClick={() => setLocId(l.id)}
              >
                {l.city ?? l.id}
              </button>
            ))}
          </div>
        )}
        <div className="answers">
          {run.prompts.map((q) => {
            const here = shownLoc
              ? q.results.filter((x) => (x.location_id ?? locations[0].id) === shownLoc)
              : q.results;
            // Questions with your name are asked in the main city only.
            if (shownLoc && shownLoc !== locations[0].id && isBranded(q)) return null;
            const asked = here.find((x) => x.prompt_text)?.prompt_text ?? q.text;
            return (
              <div key={q.id} className="question">
                <h3>
                  “{asked}” <span className="pill">{INTENT_LABELS[q.intent] ?? q.intent}</span>
                </h3>
                <ul className="result-list">
                  {run.platforms.map((p) => {
                    const rs = here.filter((x) => x.platform_key === p.key);
                    if (rs.length > 1 || (repeats && rs.length > 0 && !isBranded(q)))
                      return <RepeatRow key={p.key} label={p.label} results={rs} running={running} />;
                    return <ResultRow key={p.key} label={p.label} result={rs[0]} running={running} />;
                  })}
                </ul>
                <CheckYourself question={asked} />
              </div>
            );
          })}
        </div>
      </section>

      {run.wrong_facts.length > 0 && (
        <section className="callout">
          <h2>AI got your details wrong</h2>
          <ul>
            {run.wrong_facts.map((w, i) =>
              Object.entries(w.facts).map(([field, f]) => (
                <li key={`${i}-${field}`}>
                  {w.platform} gave your {field} as “{f.said}” (you confirmed {f.confirmed.join(" / ")}) when asked “
                  {w.prompt}”.
                </li>
              )),
            )}
          </ul>
        </section>
      )}

      <div className="two-col">
        <section className="card">
          <h2>Who they named instead</h2>
          {run.competitors.length === 0 ? (
            <p className="empty">{running ? "Waiting for answers…" : "No other businesses named."}</p>
          ) : (
            <ol className="rank-list">
              {run.competitors.slice(0, 12).map((c) => (
                <li key={c.name}>
                  <span className="truncate">{c.name}</span>
                  {c.known && <span className="pill">your competitor</span>}
                  <span className="muted small count">
                    {c.answers} answer{c.answers === 1 ? "" : "s"}
                  </span>
                </li>
              ))}
            </ol>
          )}
        </section>
        <section className="card">
          <h2>Websites they relied on</h2>
          {run.sources.length === 0 ? (
            <p className="empty">{running ? "Waiting for answers…" : "No sources cited."}</p>
          ) : (
            <ol className="rank-list">
              {run.sources.slice(0, 12).map((s) => (
                <li key={s.domain}>
                  <span className="truncate">{s.domain}</span>
                  <span className={`pill src-${s.type}`}>{SOURCE_LABELS[s.type] ?? s.type}</span>
                  <span className="muted small count">{s.answers}</span>
                </li>
              ))}
            </ol>
          )}
          <p className="hint">
            Being listed on sites that AI keeps citing can help. That's a pattern we see, not a guarantee.
          </p>
        </section>
      </div>

      {!running && (
        <div className="sticky-actions">
          <Link className="primary button-link" to={`/b/${run.business_id}/search`}>
            Next: search engines and Maps →
          </Link>
          <Link className="link-btn" to={`/b/${run.business_id}/report`}>
            Skip to your report
          </Link>
        </div>
      )}

      <p className="hint">
        These answers come from each company's API (the “API view”), asked from our server with your city in the
        question. The ChatGPT and Perplexity apps can answer differently.
      </p>
    </>
  );
}

function SearchContrast({ sc }: { sc: AISearchComparison }) {
  const line = (s: AISearchSide) =>
    `named you in ${s.named} of ${s.answers} answer${s.answers === 1 ? "" : "s"}` +
    (s.recommended ? `, recommended in ${s.recommended}` : "");
  return (
    <section className="card search-contrast">
      <h2>What AI remembers vs what it finds</h2>
      <p className="hint">
        The same questions, asked with live web search and without it (the model's own memory). Memory changes only
        when a model is retrained; search reflects the web today.
      </p>
      <div className="platform-cards">
        <div className={`stat ${sc.search_on.named ? "stat-pass" : "stat-issue"}`}>
          <span className="small">With web search</span>
          <strong>
            {sc.search_on.named} <span className="of">of {sc.search_on.answers}</span>
          </strong>
          <span className="small">{line(sc.search_on)}</span>
        </div>
        <div className={`stat ${sc.search_off.named ? "stat-pass" : "stat-issue"}`}>
          <span className="small">From memory (no search)</span>
          <strong>
            {sc.search_off.named} <span className="of">of {sc.search_off.answers}</span>
          </strong>
          <span className="small">{line(sc.search_off)}</span>
        </div>
      </div>
      {sc.competitors_only_search_off.length > 0 && (
        <p className="small">
          <strong>Only from memory: </strong>
          {sc.competitors_only_search_off.join(", ")} <span className="muted">(may be out of date or closed)</span>
        </p>
      )}
      {sc.competitors_only_search_on.length > 0 && (
        <p className="small">
          <strong>Only with search: </strong>
          {sc.competitors_only_search_on.join(", ")}
        </p>
      )}
    </section>
  );
}

/** One platform's repeat runs of a question: "Named in 2 of 3 runs", each run expandable. */
function RepeatRow({ label, results, running }: { label: string; results: AIResult[]; running: boolean }) {
  const done = results.filter((r) => r.status === "done");
  const named = done.filter((r) => r.client);
  const notDone = results.length - done.length;
  const verdict = done.length ? (
    <span className={`status ${named.length ? "status-pass" : "status-issue"}`}>
      Named in {named.length} of {done.length} run{done.length === 1 ? "" : "s"}
    </span>
  ) : (
    <span className="status status-issue">Failed</span>
  );
  const best = named.length ? Math.min(...named.map((r) => r.client?.position ?? 99)) : null;
  return (
    <li className="result">
      <details>
        <summary>
          <span className="result-platform">{label}</span>
          {verdict}
          <span className="muted small truncate">
            {best != null ? `best #${best}` : running ? "More runs coming…" : ""}
            {notDone > 0 && `${best != null ? " · " : ""}${notDone} not answered`}
          </span>
        </summary>
        <ul className="result-list repeat-runs">
          {results.map((r) => (
            <ResultRow key={r.run_id} label={`Run ${r.run_index}`} result={r} running={running} />
          ))}
        </ul>
      </details>
    </li>
  );
}

function ResultRow({ label, result, running }: { label: string; result?: AIResult; running: boolean }) {
  if (!result) {
    return (
      <li className="result pending">
        <span className="result-platform">{label}</span>
        <span className="muted small">{running ? "Waiting…" : "No answer"}</span>
      </li>
    );
  }
  let verdict: ReactNode;
  if (result.status === "skipped") verdict = <span className="status status-warning">Not run</span>;
  else if (result.status !== "done") verdict = <span className="status status-issue">Failed</span>;
  else if (result.client)
    verdict = (
      <span className="status status-pass">
        {result.client.kind === "recommended" ? "Recommended" : "Mentioned"} · #{result.client.position}
      </span>
    );
  else if (result.asked_for_location) verdict = <span className="status status-warning">Asked where you are</span>;
  else verdict = <span className="status status-issue">Not named</span>;

  return (
    <li className="result">
      <details>
        <summary>
          <span className="result-platform">{label}</span>
          {verdict}
          <span className="muted small truncate">
            {result.status !== "done"
              ? result.error
              : result.names.length
                ? result.names.slice(0, 4).join(", ") + (result.names.length > 4 ? "…" : "")
                : "No businesses named"}
          </span>
        </summary>
        <div className="answer-body">
          {result.client && <p className="fix">“{result.client.context}”</p>}
          {result.text && <p className="answer-text">{result.text}</p>}
          {result.sources.length > 0 && (
            <p className="small">
              <strong>Sources: </strong>
              {result.sources.map((s, i) => (
                <span key={i}>
                  {i > 0 && ", "}
                  <a href={s.url} target="_blank" rel="noreferrer noopener">
                    {s.domain}
                  </a>
                </span>
              ))}
            </p>
          )}
          {result.search_queries.length > 0 && (
            <p className="small muted">Searched for: {result.search_queries.join(" · ")}</p>
          )}
          <p className="small muted">Answered in {result.seconds}s</p>
        </div>
      </details>
    </li>
  );
}
