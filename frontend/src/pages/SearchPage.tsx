import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ApiError,
  searchApi,
  type Listing,
  type Press,
  type PressArticle,
  type SearchCheck,
  type SearchQueryDetail,
} from "../searchApi";
import "../search.css";

const POLL_MS = 1500;

const INTENT_LABELS: Record<string, string> = {
  category: "What you are",
  service: "A service",
  branded: "Your name",
};

const LISTING_LABELS: Record<string, string> = {
  google_business_profile: "Google Business Profile",
  apple_business_connect: "Apple Maps (Apple Business Connect)",
  bing_places: "Bing Places",
  yelp: "Yelp",
  facebook: "Facebook",
  instagram: "Instagram",
  tiktok: "TikTok",
  linkedin: "LinkedIn",
  pinterest: "Pinterest",
  youtube: "YouTube",
  twitter: "X (Twitter)",
  x: "X (Twitter)",
  nextdoor: "Nextdoor",
};

const LISTING_BADGES: Record<Listing["status"], { text: string; cls: string }> = {
  found: { text: "Found", cls: "status-pass" },
  not_found: { text: "Not found", cls: "status-issue" },
  coming_soon: { text: "Coming soon", cls: "badge-soon" },
  unknown: { text: "Couldn't check", cls: "status-warning" },
};

export function listingLabel(platform: string): string {
  return LISTING_LABELS[platform] ?? platform.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export default function SearchPage() {
  const { id = "" } = useParams();
  const [check, setCheck] = useState<SearchCheck | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const poll = useCallback(() => {
    const tick = async () => {
      try {
        const c = await searchApi.latest(id);
        setCheck(c);
        if (c.status === "running") timer.current = setTimeout(tick, POLL_MS);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Couldn't load the results.");
      }
    };
    void tick();
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const c = await searchApi.latest(id);
        if (cancelled) return;
        setCheck(c);
        if (c.status === "running") poll();
      } catch (e) {
        if (cancelled) return;
        if (!(e instanceof ApiError && e.status === 404))
          setError(e instanceof ApiError ? e.message : "Couldn't load the results.");
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [id, poll]);

  async function start() {
    setStarting(true);
    setError(null);
    try {
      await searchApi.start(id);
      poll();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't start the check.");
    } finally {
      setStarting(false);
    }
  }

  const running = check?.status === "running";

  return (
    <section className="search-page">
      <div className="page-head">
        <p className="eyebrow">Step 4 of 4 · Search engines and listings</p>
        <h1>Search, Maps and listings</h1>
        <p>
          We search Google Maps and Google the way a customer would, and check where your business shows up and which
          websites come up instead. Then we look at the business listings that maps and voice assistants rely on.
        </p>
        <p className="muted">
          <Link to={`/b/${id}/ai`}>← Back to AI assistants</Link>
        </p>
      </div>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {!loaded && (
        <div className="working" role="status">
          <span className="spinner" aria-hidden="true" />
          <span>Loading…</span>
        </div>
      )}

      {loaded && !check && (
        <div className="card">
          <h2>Check search and Maps</h2>
          <p className="hint">
            We'll run a few searches built from your profile (what you are, your main services and your name) in
            Google Maps and Google, through Google's Gemini. It takes about a minute.
          </p>
          <button type="button" className="primary" disabled={starting} onClick={start}>
            {starting ? "Starting…" : "Check search and Maps"}
          </button>
        </div>
      )}

      {check && (
        <>
          <div className={`run-status ${running ? "is-running" : ""}`} role="status" aria-live="polite">
            {running && <span className="spinner" aria-hidden="true" />}
            <span>
              {running
                ? `Searching… ${check.finished_calls} of ${check.expected_calls} searches done`
                : `${check.finished_calls} searches`}
              {check.location.city && ` · searched from ${check.location.city}`}
              {` · cost $${check.cost_usd.toFixed(3)}`}
            </span>
            {!running && (
              <button type="button" className="link-btn" disabled={starting} onClick={start}>
                {starting ? "Starting…" : "Check again"}
              </button>
            )}
          </div>
          {check.note && <p className="hint">{check.note}</p>}

          <SeenThroughGemini />

          {check.maps_skipped && (
            <p className="callout small">Google Maps was skipped: {check.maps_skipped}</p>
          )}

          <h2 className="section-title">Your searches</h2>
          <div className="search-queries">
            {check.queries.map((q) => (
              <QueryCard key={q.query} q={q} topN={check.top_n} running={running} />
            ))}
          </div>

          <Listings listings={check.summary.listings} running={running} />

          <InTheNews press={check.summary.press} pending={running && !check.summary.press} />

          {check.coming_soon.length > 0 && (
            <section className="card">
              <h2>Coming soon</h2>
              <p className="hint">
                These need data we don't have yet. Until then, you can open each link and look for yourself (sign out
                first, or use a private window, so your own history doesn't change the results).
              </p>
              <ul className="soon-list">
                {check.coming_soon.map((c) => (
                  <li key={c.key}>
                    <span>
                      <strong>{c.label}</strong>
                      <span className="badge badge-soon">Coming soon</span>
                      <span className="muted small block">Needs {c.needs}.</span>
                    </span>
                    <a href={c.check_url} target="_blank" rel="noreferrer noopener">
                      Check by hand
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      <div className="sticky-actions">
        <Link className="primary button-link" to={`/b/${id}/report`}>
          Next: your report →
        </Link>
      </div>
    </section>
  );
}

function SeenThroughGemini() {
  return (
    <aside className="seen-note">
      <strong>Seen through Gemini, not your exact ranking.</strong> We ask Google's Gemini to search Google Maps (from
      your area) and Google Search, and record the places and websites it found, in its order. That's close to what
      Google shows, but your real position changes with who searches, where, and on what device. Real Google and Bing
      rankings are coming soon.
    </aside>
  );
}

function QueryCard({ q, topN, running }: { q: SearchQueryDetail; topN: number; running: boolean }) {
  return (
    <article className="card search-query">
      <h3>
        “{q.query}” <span className="pill">{INTENT_LABELS[q.intent] ?? q.intent}</span>
      </h3>
      <div className="search-views">
        <div>
          <h4>Google Maps places (seen through Gemini)</h4>
          <MapsView q={q} topN={topN} running={running} />
        </div>
        <div>
          <h4>Websites Gemini used from Google Search</h4>
          <WebView q={q} topN={topN} running={running} />
        </div>
      </div>
      <p className="small muted check-links">
        Check it yourself:{" "}
        <a href={q.check_urls.google} target="_blank" rel="noreferrer noopener">
          Google
        </a>{" "}
        ·{" "}
        <a href={q.check_urls.bing} target="_blank" rel="noreferrer noopener">
          Bing
        </a>
      </p>
    </article>
  );
}

function ViewStatusLine({ status, error, running }: { status: string; error: string | null; running: boolean }) {
  if (status === "pending") return <p className="empty">{running ? "Searching…" : "No result."}</p>;
  if (status === "skipped") return <p className="empty">Skipped: {error}</p>;
  return <p className="empty">Couldn't search this time{error ? `: ${error}` : "."}</p>;
}

function MapsView({ q, topN, running }: { q: SearchQueryDetail; topN: number; running: boolean }) {
  const v = q.maps;
  if (v.status !== "done") return <ViewStatusLine status={v.status} error={v.error} running={running} />;
  return (
    <>
      <p className={`verdict ${v.client_rank ? "is-found" : "is-missing"}`}>
        {v.client_rank ? `You're #${v.client_rank}` : `You're not in the top ${Math.max(topN, v.results.length)}`}
      </p>
      {v.results.length === 0 ? (
        <p className="empty">No places returned.</p>
      ) : (
        <ol className="search-list">
          {v.results.map((p) => (
            <li key={p.position} className={p.is_client ? "is-client" : undefined}>
              {p.uri ? (
                <a href={p.uri} target="_blank" rel="noreferrer noopener">
                  {p.title}
                </a>
              ) : (
                p.title
              )}
              {p.is_client && <span className="pill you">You</span>}
            </li>
          ))}
        </ol>
      )}
    </>
  );
}

function WebView({ q, topN, running }: { q: SearchQueryDetail; topN: number; running: boolean }) {
  const v = q.web;
  if (v.status !== "done") return <ViewStatusLine status={v.status} error={v.error} running={running} />;
  return (
    <>
      <p className={`verdict ${v.client_rank ? "is-found" : "is-missing"}`}>
        {v.client_rank ? `Your website is #${v.client_rank}` : `Your website isn't in the top ${Math.max(topN, v.results.length)}`}
      </p>
      {v.results.length === 0 ? (
        <p className="empty">No websites returned.</p>
      ) : (
        <ol className="search-list">
          {v.results.map((s) => (
            <li key={s.domain} className={s.is_client ? "is-client" : undefined}>
              <span className="search-site">
                <span className="search-domain">{s.domain}</span>
                {s.title && <span className="muted small block">{s.title}</span>}
              </span>
              {s.is_client && <span className="pill you">Your site</span>}
            </li>
          ))}
        </ol>
      )}
    </>
  );
}

const NEWS_SHOWN = 6;

export function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? null
    : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" });
}

function ArticleList({ articles }: { articles: PressArticle[] }) {
  return (
    <ul className="news-list">
      {articles.slice(0, NEWS_SHOWN).map((a, i) => (
        <li key={`${a.url ?? a.title}-${i}`}>
          {a.url ? (
            <a href={a.url} target="_blank" rel="noreferrer noopener">
              {a.title}
            </a>
          ) : (
            a.title
          )}
          <span className="muted small block">
            {[a.source, formatDate(a.published)].filter(Boolean).join(" · ")}
          </span>
        </li>
      ))}
    </ul>
  );
}

function InTheNews({ press, pending }: { press?: Press; pending: boolean }) {
  if (!press && !pending) return null;
  const byCompetitor = new Map<string, Set<string>>();
  for (const a of press?.competitor_articles ?? []) {
    if (!a.source) continue;
    const set = byCompetitor.get(a.source) ?? new Set<string>();
    set.add(a.competitor);
    byCompetitor.set(a.source, set);
  }
  const clientPubs = new Set((press?.client_articles ?? []).map((a) => a.source).filter(Boolean));
  const competitorOnly = [...byCompetitor.entries()].filter(([pub]) => !clientPubs.has(pub));
  return (
    <section className="card news">
      <h2>
        In the news <span className="pill">Google News</span>
      </h2>
      <p className="hint">
        AI assistants often lean on local magazines and newspapers. These are articles Google News finds for your name
        and for your kind of business nearby.
      </p>
      {!press ? (
        <p className="empty">Searching Google News…</p>
      ) : (
        <div className="two-col">
          <div>
            <h3 className="news-title">Articles that name you</h3>
            {press.client_articles.length ? (
              <ArticleList articles={press.client_articles} />
            ) : (
              <p className="empty">Google News found no articles with your name.</p>
            )}
          </div>
          <div>
            <h3 className="news-title">Roundups for your kind of business</h3>
            {press.category_articles.length ? (
              <ArticleList articles={press.category_articles} />
            ) : (
              <p className="empty">No roundup articles found.</p>
            )}
            <p className="hint">Titles only: open an article to see whether you're in it.</p>
          </div>
        </div>
      )}
      {press && competitorOnly.length > 0 && (
        <>
          <h3 className="news-title">Publications that cover your competitors but not you</h3>
          <ul className="news-pubs">
            {competitorOnly.slice(0, 10).map(([pub, comps]) => (
              <li key={pub}>
                <strong>{pub}</strong>
                <span className="muted small"> wrote about {[...comps].join(", ")}</span>
              </li>
            ))}
          </ul>
          <p className="hint">These could be worth a pitch: a story, an event, or a seasonal guide.</p>
        </>
      )}
    </section>
  );
}

function Listings({ listings, running }: { listings: Listing[]; running: boolean }) {
  return (
    <section className="card">
      <h2>Business listings</h2>
      <p className="hint">
        Maps and voice assistants (Siri, Alexa, Google Assistant) mostly answer from listings, not your website. Your
        name, address, phone and hours should match everywhere.
      </p>
      <ul className="listing-list">
        {listings.map((l) => {
          const badge = LISTING_BADGES[l.status];
          const pending = running && l.status === "unknown" && l.issues.length === 0;
          return (
            <li key={l.platform}>
              <div className="listing-head">
                <strong>{listingLabel(l.platform)}</strong>
                <span className={`status ${pending ? "badge-soon" : badge.cls}`}>
                  {pending ? "Checking…" : badge.text}
                </span>
                {l.url && (
                  <a href={l.url} target="_blank" rel="noreferrer noopener" className="small">
                    {l.status === "found" ? "Open listing" : "Check by hand"}
                  </a>
                )}
              </div>
              {l.issues.length > 0 && (
                <ul className="listing-issues">
                  {l.issues.map((i) => (
                    <li key={i}>{i}</li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
      <p className="hint">
        Facebook, Instagram and other profiles come from the links on your website. Google Business Profile is checked
        by searching your name in Google Maps through Gemini.
      </p>
    </section>
  );
}
