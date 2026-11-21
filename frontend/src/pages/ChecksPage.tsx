import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, type Check, type CheckStatus, type CrawlerAccess, type CrawlerPurpose, type Foundations } from "../api";
import { Working } from "../components/Spinner";

const CHECK_TITLES: Record<string, string> = {
  http_status: "Homepage, HTTPS and redirects",
  robots_txt: "robots.txt",
  sitemap: "Sitemap",
  cdn_waf: "Firewall and bot blocking",
  js_render: "Readable without JavaScript",
  noindex: "Allowed in search results",
  canonical: "Main page address (canonical)",
  webmcp: "AI agent actions (WebMCP)",
  google_index: "Listed in Google",
  bing_index: "Listed in Bing",
  indexnow: "IndexNow",
};

const GROUPS: { status: CheckStatus[]; title: string }[] = [
  { status: ["issue"], title: "Fix first" },
  { status: ["warning", "inconclusive"], title: "Worth a look" },
  { status: ["opportunity"], title: "Opportunities" },
  { status: ["not_verified"], title: "Not verified yet" },
  { status: ["pass"], title: "Looks good" },
];

const STATUS_LABEL: Record<CheckStatus, string> = {
  pass: "Pass",
  issue: "Issue",
  warning: "Warning",
  opportunity: "Opportunity",
  not_verified: "Not verified",
  inconclusive: "Inconclusive",
};

const RESULT_LABEL: Record<CrawlerAccess["result"], string> = {
  accessible: "Can reach",
  likely_blocked: "Likely blocked",
  verified_blocked: "Blocked",
  error: "Error",
  inconclusive: "—",
};

const ROBOTS_LABEL: Record<CrawlerAccess["robots"], string> = {
  allow: "Allowed",
  disallow: "Blocked",
  no_rule: "No rule",
};

function shortUrl(u: string | null): string {
  if (!u) return "";
  try {
    const p = new URL(u);
    return p.pathname === "/" ? p.host : p.host + p.pathname;
  } catch {
    return u;
  }
}

/** Collapse per-page checks (noindex, canonical) that all passed into one card. */
export function groupChecks(checks: Check[]): Check[] {
  const out: Check[] = [];
  const perPage = new Map<string, Check[]>();
  for (const c of checks) {
    if (c.check_type === "noindex" || c.check_type === "canonical") {
      perPage.set(c.check_type, [...(perPage.get(c.check_type) ?? []), c]);
    } else out.push(c);
  }
  for (const list of perPage.values()) {
    const failing = list.filter((c) => c.status !== "pass");
    out.push(...failing);
    const passing = list.filter((c) => c.status === "pass");
    if (passing.length && !failing.length) {
      out.push({
        ...passing[0],
        target: null,
        summary: `${passing[0].summary.replace(/\.$/, "")} (${passing.length} page${passing.length > 1 ? "s" : ""} checked).`,
        evidence: { pages: passing.map((c) => c.target) },
      });
    }
  }
  return out;
}

function CheckCard({ check }: { check: Check }) {
  return (
    <article className={`check check-${check.status}`}>
      <header>
        <span className={`status status-${check.status}`}>{STATUS_LABEL[check.status]}</span>
        <h3>{CHECK_TITLES[check.check_type] ?? check.check_type}</h3>
        {check.target && (
          <a className="muted truncate" href={check.target} target="_blank" rel="noreferrer noopener">
            {shortUrl(check.target)}
          </a>
        )}
      </header>
      <p>{check.summary}</p>
      {check.fix && (
        <p className="fix">
          <strong>What to do:</strong> {check.fix}
        </p>
      )}
      {check.evidence_level === "likely" && (
        <p className="hint">Likely, not verified: based on our own test requests.</p>
      )}
      {check.evidence && Object.keys(check.evidence).length > 0 && (
        <details>
          <summary>Evidence</summary>
          <pre>{JSON.stringify(check.evidence, null, 2)}</pre>
        </details>
      )}
    </article>
  );
}

function CrawlerTable({ rows, label }: { rows: CrawlerAccess[]; label: string }) {
  return (
    <div className="table-wrap">
      <table>
        <caption>{label}</caption>
        <colgroup>
          <col className="col-crawler" />
          <col className="col-robots" />
          <col className="col-result" />
        </colgroup>
        <thead>
          <tr>
            <th scope="col">Crawler</th>
            <th scope="col">robots.txt</th>
            <th scope="col">Test request</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.token} title={r.note}>
              <th scope="row">
                {r.token}
                <span className="muted small">{r.operator}</span>
              </th>
              <td>
                <span className={`pill robots-${r.robots}`}>{ROBOTS_LABEL[r.robots]}</span>
                {r.robots_line && <code className="small">{r.robots_line}</code>}
              </td>
              <td>
                {r.token_only ? (
                  <span className="muted small">Control only, doesn't fetch</span>
                ) : (
                  <>
                    <span className={`pill result-${r.result}`}>{RESULT_LABEL[r.result]}</span>
                    {r.http_status !== null && <span className="muted small">HTTP {r.http_status}</span>}
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ChecksPage() {
  const { id = "" } = useParams();
  const [data, setData] = useState<Foundations | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async () => {
    setRunning(true);
    setError(null);
    try {
      setData(await api.runFoundations(id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "The checks didn't finish. Please try again.");
    } finally {
      setRunning(false);
    }
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    api
      .getFoundations(id)
      .then((d) => !cancelled && setData(d))
      .catch((e) => {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 404 && e.message.startsWith("No foundation")) run();
        else setError(e instanceof ApiError ? e.message : "Couldn't load the results.");
      });
    return () => {
      cancelled = true;
    };
  }, [id, run]);

  const checks = data ? groupChecks(data.checks) : [];
  const counts = (s: CheckStatus[]) => checks.filter((c) => s.includes(c.status)).length;
  const purposes: CrawlerPurpose[] = ["search", "user_fetch", "training"];

  return (
    <section className="checks">
      <div className="page-head">
        <p className="eyebrow">Step 2 of 2 · Can search engines and AI reach your site?</p>
        <h1>Website foundations</h1>
        <p>
          Before we test what AI assistants say about you, we check that they can reach and read your website. No
          AI is involved in these checks.
        </p>
        <p className="muted">
          <Link to={`/b/${id}`}>← Back to your profile</Link>
        </p>
      </div>

      {error && (
        <p className="error" role="alert">
          {error}{" "}
          <button type="button" className="link-btn" onClick={run}>
            Try again
          </button>
        </p>
      )}

      {running && (
        <Working
          intervalMs={3000}
          steps={[
            "Loading your homepage like a browser",
            "Reading robots.txt and your sitemap",
            "Visiting as 14 search and AI crawlers",
            "Comparing your page with and without JavaScript",
            "Writing up the results",
          ]}
        />
      )}

      {data && !running && (
        <>
          <div className="summary-row" aria-label="Summary">
            <div className="stat stat-issue">
              <strong>{counts(["issue"])}</strong> to fix
            </div>
            <div className="stat stat-warning">
              <strong>{counts(["warning", "inconclusive"])}</strong> to look at
            </div>
            <div className="stat stat-pass">
              <strong>{counts(["pass"])}</strong> passed
            </div>
            <div className="stat stat-not_verified">
              <strong>{counts(["not_verified"])}</strong> not verified
            </div>
          </div>
          <p className="muted small">
            Checked {new Date(data.checked_at).toLocaleString()} · {shortUrl(data.final_url)}
            {data.cdn && ` · served through ${data.cdn}`}
            {data.platform && ` · built with ${data.platform}`}
            {!data.rendered && " · JavaScript comparison not run (no browser available)"} ·{" "}
            <button type="button" className="link-btn" onClick={run}>
              Run again
            </button>
          </p>

          {GROUPS.map((g) => {
            const list = checks.filter((c) => g.status.includes(c.status));
            if (!list.length) return null;
            return (
              <section key={g.title} className="check-group">
                <h2>{g.title}</h2>
                {list.map((c, i) => (
                  <CheckCard key={`${c.check_type}-${c.target}-${i}`} check={c} />
                ))}
              </section>
            );
          })}

          <section className="card">
            <h2>Crawler access</h2>
            <p>
              Each crawler does a different job. Blocking a training crawler doesn't remove you from search, but
              blocking a search or user crawler can. We don't recommend allowing every crawler: it's your choice.
            </p>
            {purposes.map((p) => {
              const rows = data.crawlers.filter((r) => r.purpose === p);
              return rows.length ? <CrawlerTable key={p} rows={rows} label={data.purpose_labels[p]} /> : null;
            })}
            <p className="hint">
              Test requests use each crawler's name from our server. Real crawlers come from their own addresses,
              which some firewalls treat differently, so blocks are “likely”, not verified.
            </p>
          </section>
        </>
      )}
    </section>
  );
}
