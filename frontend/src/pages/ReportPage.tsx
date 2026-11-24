import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ApiError,
  reportApi,
  type Accuracy,
  type Action,
  type ActionCategory,
  type ActionCounts,
  type ActionStatus,
  type Citations,
  type Comparison,
  type Competitors,
  type FoundationsSummary,
  type Press,
  type Priority,
  type Report,
  type SearchSummary,
  type Visibility,
} from "../reportApi";
import "../report.css";

const PRIORITY_TITLES: Record<Priority, string> = {
  high: "Do these first",
  medium: "Next",
  low: "When you have time",
};

const STATUS_LABELS: Record<ActionStatus, string> = {
  not_started: "Not started",
  in_progress: "In progress",
  done: "Done",
  dismissed: "Dismissed",
};

export const CATEGORY_LABELS: Record<ActionCategory, string> = {
  indexing: "Search listing",
  crawler_access: "Crawler access",
  rendering: "Readable pages",
  citation_source: "Sources AI cites",
  entity_brand: "Facts about you",
  recommendation_evidence: "Competitors",
  content_gap: "Your website",
  reviews: "Reviews",
  listings_voice: "Maps and listings",
  agent_readiness: "AI agents",
  platform_specific: "AI assistant",
  measurement: "Measure",
};

const EFFORT_LABELS = { low: "Quick", medium: "Some work", high: "Bigger job" } as const;

const SOURCE_LABELS: Record<string, string> = {
  directory: "Directory",
  review_site: "Review site",
  social: "Social",
  forum: "Forum",
  maps: "Maps",
  marketplace: "Marketplace",
  publication: "Publication",
  own_site: "Your site",
  competitor_site: "Competitor's site",
  other: "Website",
};

const LISTING_LABELS: Record<string, string> = {
  google_business_profile: "Google Business Profile",
  gbp: "Google Business Profile",
  bing_places: "Bing Places",
  apple_maps: "Apple Maps",
  apple_business_connect: "Apple Maps",
  yelp: "Yelp",
  facebook: "Facebook",
};

const CHECK_TITLES: Record<string, string> = {
  http_status: "Homepage, HTTPS and redirects",
  robots_txt: "robots.txt",
  sitemap: "Sitemap",
  cdn_waf: "Firewall and bot blocking",
  js_render: "Readable without JavaScript",
  noindex: "Allowed in search results",
  canonical: "Main page address (canonical)",
};

export function plural(n: number, word: string, many = `${word}s`): string {
  return `${n} ${n === 1 ? word : many}`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/** Actions grouped by priority, in the order the backend sorted them. */
export function groupActions(actions: Action[]): { priority: Priority; actions: Action[] }[] {
  return (["high", "medium", "low"] as Priority[])
    .map((priority) => ({ priority, actions: actions.filter((a) => a.priority === priority) }))
    .filter((g) => g.actions.length > 0);
}

function countsOf(actions: Action[]): ActionCounts {
  const c: ActionCounts = { total: actions.length, high: 0, medium: 0, low: 0, not_started: 0, in_progress: 0, done: 0, dismissed: 0 };
  for (const a of actions) {
    c[a.priority] += 1;
    c[a.status] += 1;
  }
  return c;
}

export default function ReportPage() {
  const { id = "" } = useParams();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setReport(await reportApi.getReport(id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't load your report.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  function replaceAction(updated: Action) {
    setReport((r) => {
      if (!r) return r;
      const actions = r.actions.map((a) => (a.id === updated.id ? { ...a, ...updated } : a));
      return { ...r, actions, action_counts: countsOf(actions) };
    });
  }

  return (
    <section className="report">
      <div className="page-head">
        <p className="eyebrow">Your report</p>
        <h1>{report ? report.business.name : "Your report"}</h1>
        <p className="muted no-print">
          <Link to={`/b/${id}/ai`}>← Back to the AI answers</Link>
          {" · "}
          <Link to={`/b/${id}/checks`}>Website checks</Link>
        </p>
      </div>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!report && !error && (
        <div className="working" role="status">
          <span className="spinner" aria-hidden="true" />
          <span>Putting your report together…</span>
        </div>
      )}
      {report && <ReportBody id={id} report={report} onAction={replaceAction} onReload={load} />}
    </section>
  );
}

function ReportBody({ id, report, onAction, onReload }: {
  id: string;
  report: Report;
  onAction: (a: Action) => void;
  onReload: () => void;
}) {
  const { overview } = report;
  const nothing = !report.visibility.available && !report.foundations.available && !report.search.available;
  return (
    <>
      <div className="report-toolbar no-print">
        <button type="button" className="link-btn" onClick={() => window.print()}>
          Print or save as PDF
        </button>
        <button type="button" className="link-btn" onClick={onReload}>
          Refresh
        </button>
      </div>

      <Overview report={report} />

      <aside className="callout expectations">
        <h2>What this report can and can't tell you</h2>
        <p>
          These actions make your business easier for search engines and AI assistants to reach and understand. They
          don't guarantee a recommendation or a top spot: answers also depend on the question, the place, the
          assistant and things nobody outside those companies controls.
        </p>
        <p>
          Some AI answers come from what the AI learned in the past, and some from searching the web right now.
          Fixing your website and listings mainly helps the "searching right now" part, and can show results within
          weeks. Being known from past learning builds over months and years.
        </p>
      </aside>

      {nothing && (
        <div className="card">
          <p>
            Nothing to report yet. Start with the <Link to={`/b/${id}/checks`}>website checks</Link>, then{" "}
            <Link to={`/b/${id}/ai`}>ask the AI assistants</Link>.
          </p>
        </div>
      )}

      {report.action_counts.total > 0 && (
        <p className="action-summary">
          <a href="#actions">
            {plural(report.action_counts.total, "action")}: {report.action_counts.high} high, {report.action_counts.medium}{" "}
            medium, {report.action_counts.low} low
          </a>
          {report.action_counts.done > 0 && <span className="muted"> · {report.action_counts.done} done</span>}
        </p>
      )}

      {overview.ai_run_in_progress && (
        <p className="hint">A newer AI check is still running; this report uses the last finished one.</p>
      )}

      <VisibilitySection v={report.visibility} id={id} />
      {report.competitors.available && report.visibility.available && (
        <CompetitorSection c={report.competitors} name={report.business.name} />
      )}
      {report.citations.available && <CitationSection c={report.citations} domain={report.business.domain} />}
      {report.accuracy.available && <AccuracySection a={report.accuracy} />}
      <FoundationsSection f={report.foundations} id={id} />
      <SearchSection s={report.search} id={id} />
      {report.comparison.available && <ComparisonSection c={report.comparison} />}

      <ActionCenter id={id} actions={report.actions} counts={report.action_counts} onAction={onAction} />

      {overview.coming_soon.length > 0 && (
        <section className="report-section">
          <h2>Coming soon</h2>
          <ul className="plain-list muted">
            {overview.coming_soon.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

function Overview({ report }: { report: Report }) {
  const o = report.overview;
  const city = o.location?.city ?? report.business.city;
  return (
    <section className="report-section card" aria-labelledby="overview-title">
      <h2 id="overview-title">Overview</h2>
      <dl className="overview-grid">
        <div>
          <dt>Business</dt>
          <dd>
            {report.business.name}
            {report.business.category && <span className="muted"> · {report.business.category}</span>}
          </dd>
        </div>
        <div>
          <dt>Website</dt>
          <dd className="truncate">{report.business.domain}</dd>
        </div>
        {city && (
          <div>
            <dt>Asked about</dt>
            <dd>{city}</dd>
          </div>
        )}
        <div>
          <dt>Method</dt>
          <dd>
            <span className="pill">{o.method}</span>
          </dd>
        </div>
        {o.ai_checked_at && (
          <div>
            <dt>AI answers</dt>
            <dd>
              {formatDate(o.ai_checked_at)} · {plural(o.visibility_questions, "question")}
              {o.questions > o.visibility_questions && ` (+${o.questions - o.visibility_questions} with your name)`}
              {o.runs_per_question ? `, asked ${o.runs_per_question === 1 ? "once" : `${o.runs_per_question} times`}` : ""}
            </dd>
          </div>
        )}
        {o.platforms.length > 0 && (
          <div>
            <dt>Assistants</dt>
            <dd>{o.platforms.join(", ")}</dd>
          </div>
        )}
        {o.foundations_checked_at && (
          <div>
            <dt>Website checks</dt>
            <dd>{formatDate(o.foundations_checked_at)}</dd>
          </div>
        )}
        {o.search_checked_at && (
          <div>
            <dt>Search and maps</dt>
            <dd>{formatDate(o.search_checked_at)}</dd>
          </div>
        )}
      </dl>
      {o.skipped_platforms.map((s) => (
        <p key={s.key} className="hint">
          {s.label} was skipped: {s.reason}
        </p>
      ))}
      <details className="limitations">
        <summary>How we collected this</summary>
        <ul>
          {o.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </details>
    </section>
  );
}

function VisibilitySection({ v, id }: { v: Visibility | { available: false }; id: string }) {
  return (
    <section className="report-section" aria-labelledby="vis-title">
      <h2 id="vis-title">Do AI assistants name you?</h2>
      {!v.available ? (
        <p className="empty">
          No AI answers yet. <Link to={`/b/${id}/ai`}>Ask the AI assistants</Link>.
        </p>
      ) : (
        <>
          <p className="hint">
            Counted over answers to questions that don't use your name (API view). Answers change between runs, so
            treat small numbers as a first look, not a score.
          </p>
          <div className="platform-cards">
            {v.platforms.map((p) => (
              <div key={p.key} className={`stat ${p.named ? "stat-pass" : p.answers ? "stat-issue" : ""}`}>
                <span className="small">
                  {p.label}
                  {!p.search_enabled && " · from memory"}
                </span>
                <strong>
                  {p.named} <span className="of">of {p.answers}</span>
                </strong>
                <span className="small">
                  named you · recommended in {p.recommended}
                  {p.own_site_cited > 0 && ` · your site cited in ${p.own_site_cited}`}
                  {p.errors > 0 && ` · ${plural(p.errors, "failed call")}`}
                </span>
              </div>
            ))}
          </div>
          <p className="total-line">
            In total: named in <strong>{v.totals.named}</strong> of {plural(v.totals.answers, "answer")}, recommended in{" "}
            <strong>{v.totals.recommended}</strong>.
          </p>
        </>
      )}
    </section>
  );
}

function CompetitorSection({ c, name }: { c: Competitors; name: string }) {
  const rows = [{ name, answers: c.client.answers, you: true }, ...c.others.map((o) => ({ name: o.name, answers: o.answers, you: false }))]
    .sort((a, b) => b.answers - a.answers);
  const max = Math.max(1, ...rows.map((r) => r.answers));
  return (
    <section className="report-section" aria-labelledby="comp-title">
      <h2 id="comp-title">Who AI names: you and your competitors</h2>
      <p className="hint">How many of the {plural(c.answers, "answer")} named each business.</p>
      {rows.length === 1 ? (
        <p className="empty">The answers didn't name any other business.</p>
      ) : (
        <ol className="share-list">
          {rows.slice(0, 9).map((r) => (
            <li key={r.name} className={r.you ? "is-you" : ""}>
              <span className="share-name truncate">
                {r.name}
                {r.you && <span className="badge badge-confirmed">You</span>}
              </span>
              <span className="share-bar" aria-hidden="true">
                <span style={{ width: `${(r.answers / max) * 100}%` }} />
              </span>
              <span className="share-count">
                {r.answers} of {c.answers}
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function CitationSection({ c, domain }: { c: Citations; domain: string }) {
  return (
    <section className="report-section" aria-labelledby="cit-title">
      <h2 id="cit-title">Websites AI relies on</h2>
      <p>
        {c.answers_with_sources === 0
          ? "None of the answers listed the websites they used."
          : `${plural(c.answers_with_sources, "answer")} listed their sources. Your site (${domain}) was cited in ${c.own_site_cited}.`}
      </p>
      {c.gaps.length > 0 ? (
        <>
          <h3 className="sub-title">Sites cited next to competitors, never next to you</h3>
          <p className="hint">
            A pattern we see, not proof: we can't tell whether these sites influenced the answers.
          </p>
          <ul className="gap-list">
            {c.gaps.map((g) => (
              <li key={g.domain} className="card gap">
                <div className="gap-head">
                  <strong className="truncate">{g.domain}</strong>
                  <span className="pill">{SOURCE_LABELS[g.type ?? "other"] ?? g.type}</span>
                  <span className="muted small">{plural(g.answers, "answer")}</span>
                </div>
                {g.competitors.length > 0 && <p className="small">Named in those answers: {g.competitors.join(", ")}</p>}
                {g.prompts.length > 0 && (
                  <p className="small muted">Questions: {g.prompts.map((p) => `“${p}”`).join(", ")}</p>
                )}
              </li>
            ))}
          </ul>
        </>
      ) : (
        c.answers_with_sources > 0 && <p className="empty">No gaps: every site cited next to a competitor was also cited next to you, or none were.</p>
      )}
    </section>
  );
}

function AccuracySection({ a }: { a: Accuracy }) {
  return (
    <section className="report-section" aria-labelledby="acc-title">
      <h2 id="acc-title">Are the facts about you right?</h2>
      {a.answers_naming_you === 0 ? (
        <p className="empty">No answer named you, so there were no facts to check.</p>
      ) : a.wrong.length === 0 ? (
        <p>
          We checked {plural(a.answers_naming_you, "answer")} that named you and found no wrong phone numbers or
          addresses.
        </p>
      ) : (
        <ul className="plain-list">
          {a.wrong.map((w, i) =>
            Object.entries(w.facts).map(([fact, d]) => (
              <li key={`${i}-${fact}`} className="check check-issue">
                <p>
                  <strong>{w.platform}</strong> gave your {fact} as <strong>{d.said}</strong>; you confirmed{" "}
                  {d.confirmed.join(" / ")}.
                </p>
                <p className="small muted">Question: “{w.prompt}”</p>
              </li>
            )),
          )}
        </ul>
      )}
    </section>
  );
}

function FoundationsSection({ f, id }: { f: FoundationsSummary | { available: false }; id: string }) {
  return (
    <section className="report-section" aria-labelledby="found-title">
      <h2 id="found-title">Website foundations</h2>
      {!f.available ? (
        <p className="empty">
          Not checked yet. <Link to={`/b/${id}/checks`}>Run the website checks</Link>.
        </p>
      ) : (
        <>
          <div className="summary-row">
            <div className="stat stat-issue">
              <strong>{f.counts.issue}</strong> to fix
            </div>
            <div className="stat stat-warning">
              <strong>{f.counts.warning + f.counts.inconclusive}</strong> worth a look
            </div>
            <div className="stat">
              <strong>{f.counts.not_verified}</strong> not verified yet
            </div>
            <div className="stat stat-pass">
              <strong>{f.counts.pass}</strong> look good
            </div>
          </div>
          {f.issues.length > 0 && (
            <ul className="plain-list">
              {f.issues.map((c, i) => (
                <li key={i}>
                  <span className={`status status-${c.status}`}>{c.status === "issue" ? "Issue" : "Check"}</span>{" "}
                  <strong>{CHECK_TITLES[c.check_type] ?? c.check_type}:</strong> {c.summary}
                </li>
              ))}
            </ul>
          )}
          <p className="small no-print">
            <Link to={`/b/${id}/checks`}>See all website checks</Link>
          </p>
        </>
      )}
    </section>
  );
}

function rankText(checked: boolean, rank: number | null): string {
  if (!checked) return "—";
  return rank == null ? "Not shown" : `#${rank}`;
}

function SearchSection({ s, id }: { s: SearchSummary | { available: false }; id: string }) {
  return (
    <section className="report-section" aria-labelledby="search-title">
      <h2 id="search-title">Search, maps and listings</h2>
      {!s.available ? (
        <p className="empty">
          Not checked yet. <Link to={`/b/${id}/search`}>Check search and maps</Link>.
        </p>
      ) : (
        <>
          {(s.maps.checked > 0 || s.web.checked > 0) && (
            <p>
              {s.maps.checked > 0 && <>In map results for {s.maps.found} of {plural(s.maps.checked, "search", "searches")}. </>}
              {s.web.checked > 0 && <>In web results for {s.web.found} of {plural(s.web.checked, "search", "searches")}.</>}
            </p>
          )}
          {s.queries.length > 0 && (
            <div className="table-wrap">
              <table className="search-table">
                <thead>
                  <tr>
                    <th scope="col">Search</th>
                    <th scope="col">Maps</th>
                    <th scope="col">Web</th>
                  </tr>
                </thead>
                <tbody>
                  {s.queries.map((q) => (
                    <tr key={q.query}>
                      <th scope="row">{q.query}</th>
                      <td>{rankText(q.maps_checked, q.maps_rank)}</td>
                      <td>{rankText(q.web_checked, q.web_rank)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {s.press?.available && <PressBlock p={s.press} />}
          {s.listings.length > 0 && (
            <ul className="listing-list">
              {s.listings.map((l) => (
                <li key={l.platform}>
                  <span>{LISTING_LABELS[l.platform] ?? l.platform}</span>
                  <span className={`status listing-${l.status}`}>
                    {l.status === "found" ? "Found" : l.status === "not_found" ? "Not found" : l.status === "coming_soon" ? "Coming soon" : "Unknown"}
                  </span>
                  {l.issues.length > 0 && <span className="small muted">{l.issues.join("; ")}</span>}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

function PressBlock({ p }: { p: Press }) {
  const byDomain = new Map<string, string[]>();
  for (const a of p.competitor_articles) {
    if (!a.domain) continue;
    const names = byDomain.get(a.domain) ?? [];
    if (a.competitor && !names.includes(a.competitor)) names.push(a.competitor);
    byDomain.set(a.domain, names);
  }
  return (
    <div className="press">
      <h3 className="sub-title">In the news</h3>
      {p.client_articles.length === 0 ? (
        <p className="empty">We didn't find news articles about you.</p>
      ) : (
        <ul className="plain-list">
          {p.client_articles.map((a, i) => (
            <li key={i}>
              {a.url ? (
                <a href={a.url} target="_blank" rel="noreferrer noopener">
                  {a.title}
                </a>
              ) : (
                a.title
              )}
              <span className="muted small">
                {a.source && ` · ${a.source}`}
                {a.published && ` · ${formatDate(a.published) || a.published}`}
              </span>
            </li>
          ))}
        </ul>
      )}
      {p.competitor_only_sources.length > 0 && (
        <>
          <p className="small">Wrote about your competitors but not about you:</p>
          <ul className="plain-list small">
            {p.competitor_only_sources.map((d) => (
              <li key={d}>
                <strong>{d}</strong>
                {(byDomain.get(d) ?? []).length > 0 && <span className="muted"> · {byDomain.get(d)!.join(", ")}</span>}
              </li>
            ))}
          </ul>
          <p className="hint">A pattern we see, not a guarantee: coverage doesn't promise a recommendation.</p>
        </>
      )}
    </div>
  );
}

function change(n: number | undefined): string {
  if (n == null) return "";
  return n > 0 ? `+${n}` : `${n}`;
}

function ComparisonSection({ c }: { c: Comparison }) {
  return (
    <section className="report-section" aria-labelledby="cmp-title">
      <h2 id="cmp-title">Since your last check</h2>
      <p className="hint">Compared with the AI check on {formatDate(c.previous_checked_at)}.</p>
      {(!c.same_questions || !c.same_platforms) && (
        <p className="callout small">
          The {!c.same_questions ? "questions" : "assistants"} weren't the same both times, so the numbers can't be
          compared directly.
        </p>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Assistant</th>
              <th scope="col">Before</th>
              <th scope="col">Now</th>
              <th scope="col">Change</th>
            </tr>
          </thead>
          <tbody>
            {c.platforms.map((p) => (
              <tr key={p.key}>
                <th scope="row">{p.label}</th>
                <td>{p.before ? `${p.before.named} of ${p.before.answers}` : "—"}</td>
                <td>{p.after ? `${p.after.named} of ${p.after.answers}` : "—"}</td>
                <td>{p.named_change != null ? `${change(p.named_change)}${p.small ? " (small)" : ""}` : "—"}</td>
              </tr>
            ))}
            <tr className="total-row">
              <th scope="row">All</th>
              <td>{`${c.totals.before.named} of ${c.totals.before.answers}`}</td>
              <td>{`${c.totals.after.named} of ${c.totals.after.answers}`}</td>
              <td>
                {change(c.totals.named_change)}
                {c.totals.small ? " (small)" : ""}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="hint">{c.note}</p>
    </section>
  );
}

function ActionCenter({ id, actions, counts, onAction }: {
  id: string;
  actions: Action[];
  counts: ActionCounts;
  onAction: (a: Action) => void;
}) {
  return (
    <section className="report-section" id="actions" aria-labelledby="actions-title">
      <h2 id="actions-title">Action Center</h2>
      {actions.length === 0 ? (
        <p className="empty">No actions yet. They appear once we have checks or answers to base them on.</p>
      ) : (
        <>
          <p className="hint">
            {plural(counts.total, "action")}: {counts.high} high, {counts.medium} medium, {counts.low} low priority. Each
            one comes from something we saw in your checks or answers. Mark them as you go; when you've finished a few,
            run the same checks again to compare.
          </p>
          {groupActions(actions).map((g) => (
            <div key={g.priority} className="action-group">
              <h3 className={`priority-title priority-${g.priority}`}>
                {PRIORITY_TITLES[g.priority]} <span className="muted small">({g.actions.length})</span>
              </h3>
              <ul className="action-list">
                {g.actions.map((a) => (
                  <ActionCard key={a.id} id={id} action={a} onAction={onAction} />
                ))}
              </ul>
            </div>
          ))}
        </>
      )}
    </section>
  );
}

function ActionCard({ id, action, onAction }: { id: string; action: Action; onAction: (a: Action) => void }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function setStatus(status: ActionStatus) {
    const previous = action.status;
    setSaving(true);
    setError(null);
    onAction({ ...action, status });
    try {
      onAction(await reportApi.setActionStatus(id, action.id, status));
    } catch (e) {
      onAction({ ...action, status: previous });
      setError(e instanceof ApiError ? e.message : "Couldn't save. Try again.");
    } finally {
      setSaving(false);
    }
  }

  const closed = action.status === "done" || action.status === "dismissed";
  return (
    <li className={`action card action-${action.priority} ${closed ? "is-closed" : ""}`}>
      <header className="action-head">
        <h4>{action.title}</h4>
        <span className="pill">{CATEGORY_LABELS[action.category] ?? action.category}</span>
        <span className="pill">{EFFORT_LABELS[action.effort]}</span>
        {action.is_best_practice && <span className="badge badge-soon">General advice</span>}
      </header>
      <p>
        <strong>Why:</strong> {action.why}
      </p>
      {action.how.length > 0 && (
        <div className="fix">
          <strong>What to do:</strong>
          <ol>
            {action.how.map((h) => (
              <li key={h}>{h}</li>
            ))}
          </ol>
        </div>
      )}
      <div className="action-foot">
        <label className="status-picker no-print">
          <span className="visually-hidden">Status for {action.title}</span>
          <select
            value={action.status}
            disabled={saving}
            onChange={(e) => void setStatus(e.target.value as ActionStatus)}
          >
            {(Object.keys(STATUS_LABELS) as ActionStatus[]).map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </label>
        <span className="print-only">Status: {STATUS_LABELS[action.status]}</span>
        {action.link === "checks" && (
          <Link className="small no-print" to={`/b/${id}/checks`}>
            Open the website checks
          </Link>
        )}
        {action.evidence.length > 0 && (
          <details className="evidence no-print">
            <summary>Evidence</summary>
            <pre>{JSON.stringify(action.evidence, null, 2)}</pre>
          </details>
        )}
      </div>
      {error && (
        <p className="error small" role="alert">
          {error}
        </p>
      )}
    </li>
  );
}
