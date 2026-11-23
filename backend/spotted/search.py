"""Search engines, Maps/local pack and business listings (build step 6; plan sections 3A, 3B, 17, 21).

What we can check today, with only a Gemini key:
  maps view  Gemini + Google Maps grounding, placed at the target location (lat/lng): the places it returns,
             in order, and where the client is among them. "Google Maps places seen through Gemini".
  web view   Gemini + Google Search grounding: the websites it used, in order, and whether the client's site
             is among them. "Google Search sources seen through Gemini".
Search and Maps grounding are separate calls: one request with both is rejected (plan section 31, finding 3).

Neither is the client's real Google ranking: rankings change with the searcher's place, device and history,
and Gemini picks and orders results itself. Real Google/Bing rankings (a SERP API such as SerpApi or
DataForSEO) and the Apple Business Connect, Bing Places and Yelp listings need provider keys we don't have yet.
They sit behind small provider interfaces below and are reported as "coming_soon", with a link the owner can
use to check by hand.

Everything is stored as one audit document (config.kind "search_listings") whose `summary` field the report
reads (see `summarize`; shape documented there).
"""

import asyncio
import os
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from urllib.parse import quote_plus, urlencode
from uuid import UUID, uuid4

from pymongo import DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

from .airun import target_point
from .analysis import category_words, domain_of, norm, same_name, source_type
from .models import BusinessProfile
from .platforms import PLATFORMS, Answer, Answerer, PlatformError
from .prompts import plural, target_city
from .repo import col

METHODOLOGY_VERSION = "search-1"
KIND = "search_listings"
MAX_QUERIES = 5
MAX_SERVICE_QUERIES = 3
TOP_N = 10  # places/sources kept per query
# A run left "running" this long (server restart) is closed with what it has.
STALE_AFTER = timedelta(minutes=5)


def _timeout_s() -> float:
    return float(os.getenv("SEARCH_CALL_TIMEOUT_S", "75"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat()


# ---------------------------------------------------------------------------
# Providers for real rankings and listings (none configured yet: "coming soon")
# ---------------------------------------------------------------------------


class RankingProvider(Protocol):
    """Real search-engine results for a query at a place (a SERP API). Not implemented yet."""
    key: str

    async def results(self, query: str, city: str | None, lat: float | None, lng: float | None) -> list[dict]: ...


class ListingProvider(Protocol):
    """A business-listing directory's record for the business (Places API, Yelp Fusion...). Not implemented yet."""
    key: str

    async def find(self, name: str, city: str | None, phone: str | None) -> dict | None: ...


@dataclass(frozen=True)
class ComingSoon:
    key: str
    label: str
    needs: str  # what it would take, for the owner and for us
    env: tuple[str, ...]  # keys that would turn it on once a provider is written


COMING_SOON = [
    ComingSoon("google_rankings", "Your real Google ranking",
               "a search-results data provider (such as SerpApi or DataForSEO)", ("SERPAPI_API_KEY", "DATAFORSEO_LOGIN")),
    ComingSoon("bing_rankings", "Your real Bing ranking",
               "a search-results data provider for Bing", ("SERPAPI_API_KEY", "DATAFORSEO_LOGIN")),
    ComingSoon("apple_business_connect", "Apple Maps (Apple Business Connect)",
               "Apple Business Connect access", ("APPLE_BUSINESS_CONNECT_KEY",)),
    ComingSoon("bing_places", "Bing Places", "Bing Places / Bing Maps data access", ("BING_MAPS_KEY",)),
    ComingSoon("yelp", "Yelp", "the Yelp Fusion API", ("YELP_API_KEY",)),
]
RANKING_PROVIDERS: dict[str, RankingProvider] = {}  # none written yet
LISTING_PROVIDERS: dict[str, ListingProvider] = {}

LISTING_LABELS = {
    "google_business_profile": "Google Business Profile",
    "apple_business_connect": "Apple Maps (Apple Business Connect)",
    "bing_places": "Bing Places",
    "yelp": "Yelp",
}


def coming_soon_keys() -> list[str]:
    return [c.key for c in COMING_SOON if c.key not in RANKING_PROVIDERS and c.key not in LISTING_PROVIDERS]


def check_url(key: str, name: str, city: str | None, query: str | None = None) -> str:
    """A plain search link the owner can open to check by hand (no tracking parameters)."""
    where = f"{name} {city}" if city else name
    if key == "google_rankings":
        return "https://www.google.com/search?" + urlencode({"q": query or where})
    if key == "bing_rankings":
        return "https://www.bing.com/search?" + urlencode({"q": query or where})
    if key == "google_business_profile":
        return "https://www.google.com/maps/search/?" + urlencode({"api": 1, "query": where})
    if key == "apple_business_connect":
        return "https://maps.apple.com/?" + urlencode({"q": where})
    if key == "bing_places":
        return "https://www.bing.com/maps?" + urlencode({"q": where})
    if key == "yelp":
        params = {"find_desc": name}
        if city:
            params["find_loc"] = city
        return "https://www.yelp.com/search?" + urlencode(params)
    return "https://www.google.com/search?q=" + quote_plus(where)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def build_queries(p: BusinessProfile, city: str | None = None) -> list[dict]:
    """3-5 short search-box queries from the confirmed profile: category, top services, then the name (last)."""
    city = city or target_city(p)
    where = f" in {city}" if city else ""
    category = re.sub(r"\s+", " ", p.category.value).strip().lower() if p.category else None
    cw = category_words(p)
    out: list[dict] = []

    def add(text: str, intent: str):
        text = re.sub(r"\s+", " ", text).strip().rstrip(".")
        if text and text.lower() not in {q["text"].lower() for q in out}:
            out.append({"text": text, "intent": intent})

    if category:
        add(f"{plural(category)}{where}", "category")
    for s in p.services[:MAX_SERVICE_QUERIES]:
        service = re.sub(r"\s+", " ", s.value).strip().rstrip(".").lower()
        if not service:
            continue
        # "same-day delivery in Dallas" could be anything; "same-day delivery florist in Dallas" is a search.
        words = set(re.sub(r"[^a-z ]", " ", service).split())
        if category and not words & cw:
            service = f"{service} {category}"
        add(f"{service}{where}", "service")
    out = out[:MAX_QUERIES - 1]
    add(f"{p.name.value.strip()} {city}" if city else p.name.value.strip(), "branded")
    return out


MAPS_PROMPT = ('Search Google Maps for "{query}" near my location. List up to {n} places, best match first, '
               'one per line with only the place name. No commentary.')
WEB_PROMPT = ('Search Google for "{query}". List the websites in the results, most relevant first, one per line '
              'as "domain - page title". No commentary.')


# ---------------------------------------------------------------------------
# Reading one Gemini answer
# ---------------------------------------------------------------------------


def _text_order(items: list, text: str, key: Callable[[object], str]) -> list:
    """Order grounded items as the answer lists them; items the text doesn't name keep their order after."""
    low = (text or "").lower()
    found, rest = [], []
    for i, item in enumerate(items):
        k = (key(item) or "").lower().strip()
        pos = low.find(k) if k else -1
        (found if pos >= 0 else rest).append((pos, i, item))
    return [x[2] for x in sorted(found)] + [x[2] for x in rest]


def client_names(business: dict) -> list[str]:
    return [business["name"]] + list(business.get("aliases") or [])


def is_client_place(title: str, business: dict) -> bool:
    cw = frozenset(business.get("category_words") or [])
    return any(same_name(title, n, cw) for n in client_names(business))


def read_maps(ans: Answer, business: dict) -> tuple[list[dict], int | None]:
    """The places Gemini's Google Maps grounding returned, in order, and the client's rank (1-based) or None."""
    seen, places = set(), []
    for pl in ans.maps_places:
        # Maps grounding titles come as "DIRT Flowers - Google Maps" (live check, 24 Nov 2026).
        title = re.sub(r"\s+[-–—|]\s*Google Maps\s*$", "", (pl.get("title") or "").strip(), flags=re.I)
        key = pl.get("place_id") or title.lower()
        if not title or key in seen:
            continue
        seen.add(key)
        places.append({"title": title, "uri": pl.get("uri"), "place_id": pl.get("place_id")})
    places = _text_order(places, ans.text, lambda x: x["title"])[:TOP_N]
    rank = None
    for i, pl in enumerate(places, 1):
        pl["position"] = i
        pl["is_client"] = is_client_place(pl["title"], business)
        if pl["is_client"] and rank is None:
            rank = i
    return places, rank


def _is_client_domain(domain: str, client_domain: str) -> bool:
    return bool(client_domain) and (domain == client_domain or domain.endswith("." + client_domain))


def _titles_from_text(text: str) -> dict[str, str]:
    """'example.com - Page title' lines -> {domain: title}."""
    out = {}
    for line in (text or "").splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        m = re.match(r"^(?:https?://)?(?:www\.)?([a-z0-9.-]+\.[a-z]{2,})\S*\s+[-–—:|]\s+(.+)$", line, re.I)
        if m:
            out.setdefault(m.group(1).lower(), m.group(2).strip().strip('"*')[:200])
    return out


def read_web(ans: Answer, business: dict) -> tuple[list[dict], int | None]:
    """The websites Gemini's Google Search grounding used, in order, and the client site's rank or None."""
    client_domain = (business.get("domain") or "").lower().removeprefix("www.")
    cw = frozenset(business.get("category_words") or [])
    titles = _titles_from_text(ans.text)
    seen, sources = set(), []
    for s in ans.sources:
        d = domain_of(s.get("url"), s.get("title"))
        if not d or d in seen:
            continue
        seen.add(d)
        sources.append({"domain": d, "url": s.get("url"), "title": titles.get(d)})
    sources = _text_order(sources, ans.text, lambda x: x["domain"])[:TOP_N]
    rank = None
    for i, s in enumerate(sources, 1):
        s["position"] = i
        s["is_client"] = _is_client_domain(s["domain"], client_domain)
        s["source_type"] = source_type(s["domain"], s["url"] or "", client_domain, [], cw)
        if s["is_client"] and rank is None:
            rank = i
    return sources, rank


# ---------------------------------------------------------------------------
# Press mentions: Google News RSS (free, no key)
# ---------------------------------------------------------------------------

NEWS_RSS = "https://news.google.com/rss/search"
NEWS_MAX_ITEMS = 10
NEWS_MAX_COMPETITORS = 3
NEWS_USER_AGENT = "Mozilla/5.0 (compatible; SpottedBot/0.1)"


class NewsFetcher(Protocol):
    """Articles for a news search: [{"title", "source", "source_url", "url", "published"}]."""

    async def search(self, query: str) -> list[dict]: ...


def parse_news_rss(xml_text: str, limit: int = NEWS_MAX_ITEMS) -> list[dict]:
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    out = []
    for item in root.iter("item"):
        src = item.find("source")
        source = (src.text or "").strip() if src is not None else None
        title = (item.findtext("title") or "").strip()
        if source and title.endswith(f" - {source}"):  # Google News appends the publication to the title
            title = title[: -len(source) - 3].strip()
        published = None
        if item.findtext("pubDate"):
            try:
                published = parsedate_to_datetime(item.findtext("pubDate")).isoformat()
            except (TypeError, ValueError):
                published = None
        if title:
            out.append({"title": title, "source": source or None,
                        "source_url": src.get("url") if src is not None else None,
                        "url": (item.findtext("link") or "").strip() or None, "published": published})
        if len(out) >= limit:
            break
    return out


class GoogleNewsRSS:
    """Google News RSS search, US English. Cached per query for the life of the object (one run)."""

    def __init__(self, timeout_s: float = 10.0):
        self._timeout = timeout_s
        self._cache: dict[str, list[dict]] = {}

    async def search(self, query: str) -> list[dict]:
        if query in self._cache:
            return self._cache[query]
        import httpx

        async with httpx.AsyncClient(timeout=self._timeout, headers={"User-Agent": NEWS_USER_AGENT},
                                     follow_redirects=True) as http:
            r = await http.get(NEWS_RSS, params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
        items = parse_news_rss(r.text) if r.status_code == 200 else []
        self._cache[query] = items
        return items


def news_queries(business: dict, category: str | None) -> list[dict]:
    """Branded (quoted name + city), category roundups, and the top competitors (quoted name + city)."""
    city = business.get("city")
    near = f" {city}" if city else ""
    qs = [{"kind": "client", "query": f'"{business["name"]}"{near}'}]
    if category:
        qs.append({"kind": "category", "query": f"best {plural(category)}{near}"})
    for c in (business.get("competitors") or [])[:NEWS_MAX_COMPETITORS]:
        qs.append({"kind": "competitor", "competitor": c, "query": f'"{c}"{near}'})
    return qs


async def run_news(news: NewsFetcher, queries: list[dict]) -> list[dict]:
    async def one(q):
        try:
            items = await asyncio.wait_for(news.search(q["query"]), _timeout_s())
            return {**q, "status": "done", "error": None, "items": items[:NEWS_MAX_ITEMS]}
        except Exception as exc:  # the news check never sinks the run
            return {**q, "status": "error", "error": f"{type(exc).__name__}: {str(exc)[:200]}", "items": []}

    return list(await asyncio.gather(*(one(q) for q in queries)))


def _source_domain(url: str | None) -> str:
    return domain_of(url, None) if url else ""


def press_summary(press: list[dict]) -> dict:
    keys = ("title", "source", "source_url", "url", "published")
    client = [{k: a.get(k) for k in keys} for p in press if p["kind"] == "client" for a in p["items"]]
    category = [{k: a.get(k) for k in keys} for p in press if p["kind"] == "category" for a in p["items"]]
    comp = [{"competitor": p["competitor"], **{k: a.get(k) for k in keys}}
            for p in press if p["kind"] == "competitor" for a in p["items"]]
    client_sources = list(dict.fromkeys(d for a in client if (d := _source_domain(a["source_url"]))))
    comp_only = list(dict.fromkeys(d for a in comp if (d := _source_domain(a["source_url"])) and d not in client_sources))
    return {"client_articles": client, "category_articles": category, "competitor_articles": comp,
            "client_sources": client_sources, "competitor_only_sources": comp_only}


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------


def listings_from(audit: dict) -> list[dict]:
    """Listing status per platform from the Maps results and the confirmed social profiles."""
    business = audit["config"]["business"]
    name, city = business["name"], business.get("city")
    results = audit.get("results", [])
    maps = [r for r in results if r["view"] == "maps"]
    out = []

    # Google Business Profile: a place matching the name in Maps, the branded search first.
    gbp = {"platform": "google_business_profile", "status": "not_found", "url": None, "issues": []}
    ordered = sorted((r for r in maps if r["status"] == "done"), key=lambda r: r["intent"] != "branded")
    match = next(((r, pl) for r in ordered for pl in r["places"] if pl["is_client"]), None)
    branded = next((r for r in maps if r["intent"] == "branded"), None)
    site_link = next((s["url"] for s in business.get("social_profiles", []) if s["platform"] == "google_maps"), None)
    if match:
        r, pl = match
        gbp.update(status="found", url=pl.get("uri") or site_link or check_url("google_business_profile", name, city))
        if not any(norm(pl["title"]) == norm(n) for n in client_names(business)):
            gbp["issues"].append(f"Google Maps shows your name as “{pl['title']}”, but your confirmed name is "
                                 f"“{name}”. Use the same name everywhere so people and AI know it's you.")
        if r["intent"] != "branded" and branded and branded["status"] == "done":
            gbp["issues"].append(f"A Google Maps search for “{branded['query']}” didn't return you, though "
                                 f"another search did.")
    elif audit["config"].get("maps_skipped"):
        gbp.update(status="unknown", url=site_link or check_url("google_business_profile", name, city),
                   issues=[f"We couldn't check Google Maps: {audit['config']['maps_skipped']}"])
    elif audit.get("status") == "running" and len(maps) < len(audit["config"]["queries"]):
        gbp.update(status="unknown", url=site_link or check_url("google_business_profile", name, city))
    elif not any(r["status"] == "done" for r in maps):
        gbp.update(status="unknown", url=site_link or check_url("google_business_profile", name, city),
                   issues=["We couldn't reach Google Maps this time. Try again."])
    else:
        q = branded["query"] if branded else name
        gbp.update(url=site_link or check_url("google_business_profile", name, city),
                   issues=[f"Google Maps didn't return your business when we searched for “{q}”. "
                           "Check that you have a verified Google Business Profile with this name."])
        if site_link:
            gbp["issues"].append("Your website links to a Google Maps listing; check that it is verified and "
                                 "shows your current name, address and hours.")
    out.append(gbp)

    for key in ("apple_business_connect", "bing_places", "yelp"):
        out.append({"platform": key, "status": "coming_soon", "url": check_url(key, name, city), "issues": []})

    seen = set()
    for s in business.get("social_profiles", []):
        if s["platform"] == "google_maps" or s["platform"] in seen:
            continue
        seen.add(s["platform"])
        out.append({"platform": s["platform"], "status": "found", "url": s["url"], "issues": []})
    return out


# ---------------------------------------------------------------------------
# The summary (read by the report)
# ---------------------------------------------------------------------------


def _view_result(audit: dict, i: int, view: str) -> dict | None:
    return next((r for r in audit.get("results", []) if r["query_index"] == i and r["view"] == view), None)


def summarize(audit: dict) -> dict:
    """The stored summary, exactly:
    {"checked_at": iso,
     "queries": [{"query": str,
                  "maps": {"client_rank": int|null, "results": [str]},
                  "web": {"client_rank": int|null, "results": [{"domain": str, "title": str|null}]}}],
     "listings": [{"platform": str, "status": "found"|"not_found"|"coming_soon"|"unknown",
                   "url": str|null, "issues": [str]}],
     "coming_soon": [str],
     "press": {...}}   # optional: Google News articles, only when the news check ran (see press_summary)
    For listings that are not "found", url is a search link the owner can use to check by hand.
    """
    queries = []
    for i, q in enumerate(audit["config"]["queries"]):
        m = _view_result(audit, i, "maps")
        w = _view_result(audit, i, "web")
        queries.append({
            "query": q["text"],
            "maps": {"client_rank": m["client_rank"] if m else None,
                     "results": [pl["title"] for pl in m["places"]] if m else []},
            "web": {"client_rank": w["client_rank"] if w else None,
                    "results": [{"domain": s["domain"], "title": s["title"]} for s in w["sources"]] if w else []},
        })
    checked = audit.get("finished_at") or audit.get("started_at")
    out = {"checked_at": _iso(checked), "queries": queries, "listings": listings_from(audit),
           "coming_soon": list(audit["config"].get("coming_soon", coming_soon_keys()))}
    if audit.get("press") is not None:
        out["press"] = press_summary(audit["press"])
    return out


def details(audit: dict) -> dict:
    """What the page shows: the summary plus per-query details and run status."""
    cfg = audit["config"]
    business = cfg["business"]
    queries = []
    for i, q in enumerate(cfg["queries"]):
        views = {}
        for view in ("maps", "web"):
            r = _view_result(audit, i, view)
            if r is None:
                skipped = cfg.get("maps_skipped") if view == "maps" else None
                views[view] = {"status": "skipped" if skipped else "pending", "error": skipped,
                               "client_rank": None, "results": [], "seconds": None, "search_queries": []}
                continue
            views[view] = {
                "status": r["status"], "error": r["error"], "client_rank": r["client_rank"],
                "results": r["places"] if view == "maps" else r["sources"],
                "seconds": round((r["latency_ms"] or 0) / 1000, 1) if r["latency_ms"] else None,
                "search_queries": r.get("search_queries", []),
            }
        queries.append({"query": q["text"], "intent": q["intent"], **views,
                        "check_urls": {"google": check_url("google_rankings", business["name"], None, q["text"]),
                                       "bing": check_url("bing_rankings", business["name"], None, q["text"])}})
    first_query = cfg["queries"][0]["text"] if cfg["queries"] else None
    return {
        "audit_id": audit["_id"], "business_id": audit["business_id"], "status": audit["status"],
        "started_at": _iso(audit.get("started_at")), "finished_at": _iso(audit.get("finished_at")),
        "expected_calls": audit["expected_calls"], "finished_calls": len(audit.get("results", [])),
        "location": cfg["location"], "maps_skipped": cfg.get("maps_skipped"), "top_n": TOP_N,
        "cost_usd": round(audit.get("cost_usd", 0.0), 4), "note": audit.get("note"),
        "summary": audit.get("summary") or summarize(audit),
        "queries": queries,
        "news": {"status": "pending" if audit.get("press") is None and audit["status"] == "running"
                 else "done" if audit.get("press") is not None else "not_run",
                 "errors": [p["error"] for p in audit.get("press") or [] if p["status"] != "done"],
                 "queries": [q["query"] for q in cfg.get("news_queries", [])]},
        "coming_soon": [{"key": c.key, "label": c.label, "needs": c.needs,
                         "check_url": check_url(c.key, business["name"], business.get("city"), first_query)}
                        for c in COMING_SOON if c.key in cfg.get("coming_soon", [])],
    }


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


def _business(p: BusinessProfile, city: str | None) -> dict:
    return {"name": p.name.value.strip(), "aliases": [a.value for a in p.aliases if a.value.strip()],
            "domain": p.domain.lower().removeprefix("www."), "city": city,
            "category_words": sorted(category_words(p)),
            "social_profiles": [{"platform": s.platform, "url": s.url} for s in p.social_profiles],
            "competitors": [c.value.strip() for c in p.suggested_competitors if c.value.strip()]}


async def create_search_audit(db: AsyncDatabase, business_id: UUID, profile: BusinessProfile) -> dict:
    where = target_point(profile)
    city = where.get("city") or target_city(profile)
    queries = build_queries(profile, city)
    business = _business(profile, city)
    category = re.sub(r"\s+", " ", profile.category.value).strip().lower() if profile.category else None
    maps_skipped = None if where.get("lat") is not None else \
        "We don't have a map position for your location yet. Add a street address or city to your profile."
    now = _now()
    doc = {
        "_id": str(uuid4()), "business_id": str(business_id), "tier": "free", "status": "running",
        "methodology_version": METHODOLOGY_VERSION,
        "config": {"kind": KIND, "queries": queries, "location": where, "maps_skipped": maps_skipped,
                   "business": business, "coming_soon": coming_soon_keys(),
                   "news_queries": news_queries(business, category),
                   "views": {"maps": "gemini + google_maps grounding at lat/lng",
                             "web": "gemini + google_search grounding", "news": "google news rss, en-US"}},
        "results": [], "expected_calls": len(queries) * (1 if maps_skipped else 2),
        "cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0,
        "press": None, "started_at": now, "finished_at": None, "created_at": now, "summary": None,
    }
    await col(db, "audits").insert_one(doc)
    return doc


async def run_view(answerer: Answerer, view: str, query: dict, index: int, where: dict, business: dict) -> dict:
    """One Gemini call (Maps or Search grounding, never both) for one query, read into a result record."""
    plat = PLATFORMS["gemini_maps" if view == "maps" else "gemini_search"]
    prompt = (MAPS_PROMPT if view == "maps" else WEB_PROMPT).format(query=query["text"], n=TOP_N)
    lat, lng = (where.get("lat"), where.get("lng")) if view == "maps" else (None, None)
    r = {"query_index": index, "query": query["text"], "intent": query["intent"], "view": view,
         "grounding": plat.grounding, "lat": lat, "lng": lng, "prompt": prompt, "status": "done", "error": None,
         "model": None, "latency_ms": None, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "text": "",
         "search_queries": [], "places": [], "sources": [], "client_rank": None, "finished_at": None}
    try:
        ans = await asyncio.wait_for(answerer.answer(plat, prompt, lat, lng), _timeout_s())
        r.update(model=ans.model, latency_ms=ans.latency_ms, tokens_in=ans.tokens_in, tokens_out=ans.tokens_out,
                 cost_usd=ans.cost_usd, text=ans.text[:8000], search_queries=ans.search_queries)
        if view == "maps":
            r["places"], r["client_rank"] = read_maps(ans, business)
        else:
            r["sources"], r["client_rank"] = read_web(ans, business)
    except (TimeoutError, asyncio.TimeoutError):
        r.update(status="timeout", error=f"No answer within {_timeout_s():.0f} seconds.")
    except PlatformError as exc:
        r.update(status="timeout" if "within" in str(exc) else "error", error=str(exc))
    except Exception as exc:  # one failed call never sinks the run
        r.update(status="error", error=f"{type(exc).__name__}: {str(exc)[:200]}")
    r["finished_at"] = _now()
    return r


async def run_all(answerer: Answerer, audit: dict,
                  on_result: Callable[[dict], Awaitable[None]] | None = None) -> list[dict]:
    """Every query x view in parallel; `on_result` is called as each finishes (to save it). No database here."""
    cfg = audit["config"]
    views = ["web"] if cfg.get("maps_skipped") else ["maps", "web"]

    async def one(i, q, view):
        r = await run_view(answerer, view, q, i, cfg["location"], cfg["business"])
        if on_result:
            await on_result(r)
        return r

    return list(await asyncio.gather(*(one(i, q, v) for i, q in enumerate(cfg["queries"]) for v in views)))


def final_status(results: list[dict]) -> str:
    statuses = [r["status"] for r in results]
    if statuses and all(s == "done" for s in statuses):
        return "complete"
    return "partial" if any(s == "done" for s in statuses) else "failed"


async def execute(db: AsyncDatabase, audit: dict, answerer: Answerer, news: NewsFetcher | None = None) -> None:
    audits = col(db, "audits")

    async def press() -> None:
        if news is None or not audit["config"].get("news_queries"):
            return
        found = await run_news(news, audit["config"]["news_queries"])
        await audits.update_one({"_id": audit["_id"]}, {"$set": {"press": found}})

    async def save(r: dict) -> None:
        update = {"$push": {"results": r},
                  "$inc": {"cost_usd": r["cost_usd"], "tokens_in": r["tokens_in"], "tokens_out": r["tokens_out"]}}
        if r["status"] == "done":
            update["$min"] = {"first_results_at": r["finished_at"]}
        await audits.update_one({"_id": audit["_id"]}, update)

    try:
        results, _ = await asyncio.gather(run_all(answerer, audit, save), press())
        status = final_status(results)
    except Exception:
        status = "failed"
    await audits.update_one({"_id": audit["_id"]}, {"$set": {"status": status, "finished_at": _now()}})
    done = await audits.find_one({"_id": audit["_id"]})
    await audits.update_one({"_id": audit["_id"]}, {"$set": {"summary": summarize(done)}})


# ---------------------------------------------------------------------------
# Reading back
# ---------------------------------------------------------------------------


async def latest_search_audit(db: AsyncDatabase, business_id: UUID | str) -> dict | None:
    audits = col(db, "audits")
    audit = await audits.find_one({"business_id": str(business_id), "config.kind": KIND},
                                  sort=[("created_at", DESCENDING)])
    if audit and audit["status"] == "running":
        started = audit["started_at"]
        started = started if started.tzinfo else started.replace(tzinfo=timezone.utc)
        if _now() - started > STALE_AFTER:  # left running by a restart
            status = final_status(audit.get("results", []))
            audit.update(status=status, finished_at=_now(), note="Stopped early: the server restarted.")
            audit["summary"] = summarize(audit)
            await audits.update_one({"_id": audit["_id"]}, {"$set": {
                "status": status, "finished_at": audit["finished_at"], "note": audit["note"],
                "summary": audit["summary"]}})
    return audit


async def latest_search_summary(db: AsyncDatabase, business_id: UUID | str) -> dict | None:
    """The latest search & listings summary for a business (shape in `summarize`), or None if never run."""
    audit = await latest_search_audit(db, business_id)
    if audit is None:
        return None
    return audit.get("summary") or summarize(audit)
