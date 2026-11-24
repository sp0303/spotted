"""Foundation checks (build order step 2; plan Update 1 sections 1-2 and Update 2 sections 18-23).

No AI calls. Each check produces a plain-language summary for the owner, a status, an evidence
level and the raw evidence. Limits are stated, never hidden: a user-agent test from our server is
not the real crawler, and nothing here can see Search Console or Bing Webmaster Tools data.
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from . import robots as robots_mod
from .crawl import FetchError, Page, Site, fetch_page, fetch_site, make_client, normalize_url, registrable_domain
from .crawlers import CRAWLERS
from .extract import page_text
from .render import Renderer, RenderResult, default_renderer

METHODOLOGY_VERSION = "foundations-v1"
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

CHALLENGE_MARKERS = [
    ("cloudflare", re.compile(r"Just a moment\.\.\.|cf-chl-|challenge-platform|Attention Required! \| Cloudflare", re.I)),
    ("imperva", re.compile(r"Incapsula incident|_Incapsula_Resource", re.I)),
    ("sucuri", re.compile(r"Sucuri WebSite Firewall|Access Denied - Sucuri", re.I)),
    ("akamai", re.compile(r"Reference #\d+\.[0-9a-f]+\.\d+|AkamaiGHost", re.I)),
    ("generic", re.compile(r"captcha|are you a robot|verify you are human|bot protection|access denied", re.I)),
]


@dataclass
class CheckResult:
    check_type: str  # check_type enum
    status: str  # check_status enum: pass | issue | warning | opportunity | not_verified | inconclusive
    summary: str
    target: str | None = None
    evidence_level: str = "observed"
    evidence: dict = field(default_factory=dict)
    fix: str | None = None  # what the owner can do, when there's something to do


@dataclass
class CrawlerResult:
    token: str
    operator: str
    purpose: str
    url: str
    robots: str  # allow | disallow | no_rule
    robots_line: str | None
    http_status: int | None
    challenge: bool | None
    result: str  # accessible | likely_blocked | verified_blocked | error | inconclusive
    cdn: str | None
    note: str
    token_only: bool = False


@dataclass
class FoundationReport:
    url: str
    final_url: str
    cdn: str | None
    platform: str | None
    checks: list[CheckResult]
    crawlers: list[CrawlerResult]
    rendered: bool  # whether the JavaScript render ran


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def detect_cdn(headers: dict[str, str]) -> str | None:
    server = headers.get("server", "").lower()
    if "cf-ray" in headers or "cloudflare" in server:
        return "cloudflare"
    if "x-akamai-transformed" in headers or "akamai" in server or "x-akamai-request-id" in headers:
        return "akamai"
    if "x-sucuri-id" in headers or "sucuri" in server:
        return "sucuri"
    if "x-iinfo" in headers or "incap_ses" in headers.get("set-cookie", ""):
        return "imperva"
    if "x-amz-cf-id" in headers or "cloudfront" in headers.get("via", "").lower():
        return "cloudfront"
    if "x-fastly-request-id" in headers or "fastly" in headers.get("x-served-by", "").lower():
        return "fastly"
    if "x-vercel-id" in headers or server == "vercel":
        return "vercel"
    if "x-nf-request-id" in headers or server == "netlify":
        return "netlify"
    return None


def detect_platform(page: Page) -> str | None:
    h, html = page.headers, page.html[:200_000]
    if "x-wix-request-id" in h or "static.wixstatic.com" in html:
        return "wix"
    if "squarespace" in h.get("server", "").lower() or "static1.squarespace.com" in html:
        return "squarespace"
    if "x-shopid" in h or "cdn.shopify.com" in html:
        return "shopify"
    if "/wp-content/" in html or "/wp-includes/" in html:
        return "wordpress"
    if "webflow" in html[:20_000].lower():
        return "webflow"
    if "__NEXT_DATA__" in html:
        return "next.js"
    return None


def detect_challenge(page: Page) -> str | None:
    if page.headers.get("cf-mitigated") == "challenge":
        return "cloudflare"
    if page.status in (401, 403, 429, 503) or len(page.html) < 20_000:
        head = page.html[:20_000]
        for name, pattern in CHALLENGE_MARKERS:
            if pattern.search(head):
                return name
    return None


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def _contains_phone(text: str, phone: str) -> bool:
    want = _digits(phone)[-10:]
    return len(want) >= 7 and want in _digits(text)


def _contains_name(text: str, name: str) -> bool:
    norm = lambda s: re.sub(r"[^0-9a-z]+", " ", s.lower()).strip()  # noqa: E731
    return bool(norm(name)) and norm(name) in norm(text)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_http(home: Page, http_probe: Page | Exception | None) -> CheckResult:
    chain = [{"url": u, "status": s} for u, s in home.redirects] + [{"url": home.url, "status": home.status}]
    evidence = {"chain": chain}
    if home.status >= 400:
        return CheckResult("http_status", "issue", f"Your homepage returns an error (HTTP {home.status}).",
                           home.url, evidence=evidence, fix="Fix the server error so the homepage loads.")
    if not home.url.startswith("https://"):
        return CheckResult("http_status", "issue", "Your site doesn't use HTTPS.", home.url, evidence=evidence,
                           fix="Turn on HTTPS (most hosts offer a free certificate) and redirect http:// to https://.")
    if isinstance(http_probe, Page):
        evidence["http_version"] = [{"url": u, "status": s} for u, s in http_probe.redirects] + [
            {"url": http_probe.url, "status": http_probe.status}]
        if not http_probe.url.startswith("https://"):
            return CheckResult("http_status", "warning",
                               "The http:// version of your site doesn't redirect to https://.", home.url,
                               evidence=evidence, fix="Redirect every http:// address to its https:// version.")
    if len(home.redirects) > 2:
        return CheckResult("http_status", "warning",
                           f"Your homepage goes through {len(home.redirects)} redirects before it loads.", home.url,
                           evidence=evidence, fix="Link and redirect straight to the final address.")
    return CheckResult("http_status", "pass", "Your homepage loads over HTTPS without errors.", home.url,
                       evidence=evidence)


def check_robots(robots_page: Page | Exception | None, robots: robots_mod.Robots | None, home_url: str) -> CheckResult:
    target = urljoin(home_url, "/robots.txt")
    if isinstance(robots_page, Exception) or robots_page is None:
        return CheckResult("robots_txt", "inconclusive", "We couldn't load your robots.txt file.", target,
                           evidence={"error": str(robots_page)})
    if robots_page.status >= 500:
        return CheckResult("robots_txt", "issue",
                           f"Your robots.txt returns a server error (HTTP {robots_page.status}). "
                           "Google treats this as 'don't crawl anything' until it's fixed.", target,
                           evidence={"status": robots_page.status},
                           fix="Make /robots.txt return a normal page (or a 404 if you don't want one).")
    if robots_page.status >= 400 or robots is None:
        return CheckResult("robots_txt", "pass",
                           "You don't have a robots.txt file, so all crawlers are allowed by default.", target,
                           evidence={"status": robots_page.status})
    blocked = [c.token for c in CRAWLERS if c.purpose == "search" and c.token in ("Googlebot", "Bingbot")
               and robots_mod.check(robots, c.token, home_url).rule == "disallow"]
    evidence = {"status": robots_page.status, "groups": [g.agents for g in robots.groups],
                "sitemaps": robots.sitemaps, "invalid_lines": robots.invalid_lines[:20],
                "text": robots_page.html[:5000]}
    if blocked:
        return CheckResult("robots_txt", "issue",
                           f"Your robots.txt blocks {' and '.join(blocked)} from your homepage, "
                           "so it can't appear in that search engine.", target, evidence=evidence,
                           fix="Remove the Disallow rule that applies to these crawlers.")
    if robots.invalid_lines:
        return CheckResult("robots_txt", "warning",
                           f"Your robots.txt has {len(robots.invalid_lines)} line(s) crawlers won't understand.",
                           target, evidence=evidence, fix="Check the lines listed in the evidence for typos.")
    return CheckResult("robots_txt", "pass", "Your robots.txt is readable and doesn't block Google or Bing.",
                       target, evidence=evidence)


def _parse_sitemap(xml: str) -> tuple[str, list[str]]:
    """Return (kind, locs) where kind is 'urlset', 'sitemapindex' or 'invalid'."""
    try:
        root = ET.fromstring(xml.encode("utf-8", errors="replace"))
    except ET.ParseError:
        return "invalid", []
    tag = root.tag.rsplit("}", 1)[-1]
    # Only the page/sitemap address of each entry: <url><loc> or <sitemap><loc>. Extensions such as
    # <image:image><image:loc> (Shopify lists product images on its CDN) aren't pages and aren't off-site links.
    locs = [loc.text.strip() for entry in root for loc in entry
            if loc.tag.rsplit("}", 1)[-1] == "loc" and loc.text and loc.tag.split("}")[0] == entry.tag.split("}")[0]]
    return (tag if tag in ("urlset", "sitemapindex") else "invalid"), locs


async def check_sitemap(client: httpx.AsyncClient, home_url: str, robots: robots_mod.Robots | None) -> CheckResult:
    listed = list(robots.sitemaps) if robots else []
    candidates = listed or [urljoin(home_url, "/sitemap.xml"), urljoin(home_url, "/sitemap_index.xml")]
    domain = registrable_domain(home_url)
    tried = []
    for sm_url in candidates[:3]:
        try:
            sm_url = normalize_url(sm_url)
            page = await fetch_page(client, sm_url)
        except FetchError as exc:
            tried.append({"url": sm_url, "error": str(exc)})
            continue
        tried.append({"url": sm_url, "status": page.status})
        if page.status >= 400:
            continue
        kind, locs = _parse_sitemap(page.html)
        if kind == "invalid":
            return CheckResult("sitemap", "issue", "Your sitemap exists but isn't valid XML.", sm_url,
                               evidence={"tried": tried}, fix="Regenerate the sitemap with your site builder or SEO plugin.")
        urls = locs
        children = []
        if kind == "sitemapindex":
            children = locs[:3]
            urls = []
            for child in children:
                try:
                    cp = await fetch_page(client, normalize_url(child))
                    if cp.status < 400:
                        urls += _parse_sitemap(cp.html)[1]
                except FetchError:
                    pass
        off_site = [u for u in urls if registrable_domain(u) != domain]
        home_listed = any(u.rstrip("/") == home_url.rstrip("/") for u in urls)
        evidence = {"tried": tried, "kind": kind, "child_sitemaps": children, "url_count": len(urls),
                    "sample": urls[:10], "off_site": off_site[:10], "listed_in_robots": bool(listed)}
        if not urls:
            return CheckResult("sitemap", "warning", "Your sitemap is empty.", sm_url, evidence=evidence,
                               fix="Make sure your important pages are included in the sitemap.")
        if off_site:
            return CheckResult("sitemap", "warning",
                               f"{len(off_site)} sitemap address(es) point to a different domain.", sm_url,
                               evidence=evidence, fix="List only addresses on your own domain.")
        more = "" if kind == "urlset" else f" (from {len(children)} of the sitemaps in your index)"
        note = "" if listed else " It isn't listed in robots.txt; adding a 'Sitemap:' line helps crawlers find it."
        status = "pass" if listed else "warning"
        summary = f"Your sitemap lists {len(urls)} page(s){more}." + note
        if not home_listed and kind == "urlset":
            summary += " Your homepage isn't in it."
        return CheckResult("sitemap", status, summary, sm_url, evidence=evidence,
                           fix=None if listed else f"Add 'Sitemap: {sm_url}' to robots.txt.")
    return CheckResult("sitemap", "warning", "We couldn't find a sitemap.", candidates[0], evidence={"tried": tried},
                       fix="Create a sitemap (most site builders and SEO plugins make one) and list it in robots.txt. "
                           "Then submit it in Google Search Console and Bing Webmaster Tools.")


def _robots_meta(page: Page) -> dict:
    soup = BeautifulSoup(page.html, "html.parser")
    metas = {}
    for m in soup.find_all("meta", attrs={"name": True, "content": True}):
        name = m["name"].strip().lower()
        if name in ("robots", "googlebot", "bingbot"):
            metas[name] = m["content"].lower()
    canon = soup.find("link", rel=lambda v: v and "canonical" in (v if isinstance(v, list) else [v]))
    return {"meta": metas, "x_robots_tag": page.headers.get("x-robots-tag", "").lower(),
            "canonical": canon.get("href", "").strip() if canon else None}


def check_noindex(pages: list[Page]) -> list[CheckResult]:
    out = []
    for page in pages:
        info = _robots_meta(page)
        sources = [f"meta {k}: {v}" for k, v in info["meta"].items() if "noindex" in v or "none" == v.strip()]
        if "noindex" in info["x_robots_tag"]:
            sources.append(f"X-Robots-Tag: {info['x_robots_tag']}")
        if sources:
            out.append(CheckResult("noindex", "issue",
                                   "This page tells search engines not to list it (noindex).", page.url,
                                   evidence={"found": sources},
                                   fix="Remove the noindex setting (often a 'hide from search engines' option in your site builder)."))
        else:
            out.append(CheckResult("noindex", "pass", "Search engines are allowed to list this page.", page.url,
                                   evidence=info))
    return out


def check_canonical(pages: list[Page]) -> list[CheckResult]:
    out = []
    for i, page in enumerate(pages):
        canon = _robots_meta(page)["canonical"]
        if not canon:
            out.append(CheckResult("canonical", "pass", "No canonical tag; search engines will use this address.",
                                   page.url))
            continue
        target = urljoin(page.url, canon)
        evidence = {"canonical": target}
        if registrable_domain(target) != registrable_domain(page.url):
            out.append(CheckResult("canonical", "issue",
                                   f"This page says its main version is on another domain ({urlsplit(target).hostname}).",
                                   page.url, evidence=evidence,
                                   fix="Point the canonical tag at this page's own address."))
        elif i == 0 and urlsplit(target).path.rstrip("/") != urlsplit(page.url).path.rstrip("/"):
            out.append(CheckResult("canonical", "warning",
                                   "Your homepage says its main version is a different page.", page.url,
                                   evidence=evidence, fix="Set the homepage's canonical tag to the homepage itself."))
        else:
            out.append(CheckResult("canonical", "pass", "The canonical tag points to this site.", page.url,
                                   evidence=evidence))
    return out


async def check_crawlers(client: httpx.AsyncClient, home: Page, robots: robots_mod.Robots | None,
                         cdn: str | None) -> tuple[list[CrawlerResult], CheckResult]:
    baseline_words = _word_count(page_text(home))
    baseline_challenge = detect_challenge(home)
    active = [c for c in CRAWLERS if not c.is_token_only]
    fetched = await asyncio.gather(
        *(fetch_page(client, home.url, headers={"User-Agent": c.user_agent}) for c in active),
        return_exceptions=True,
    )
    by_token = dict(zip((c.token for c in active), fetched))
    results: list[CrawlerResult] = []
    for c in CRAWLERS:
        verdict = robots_mod.check(robots, c.token, home.url) if robots else robots_mod.Verdict("no_rule", None, None)
        robots_note = {
            "disallow": f"robots.txt blocks it ({verdict.matched}, group '{verdict.group}').",
            "allow": f"robots.txt has rules for it and allows the homepage (group '{verdict.group}').",
            "no_rule": "robots.txt has no rule that blocks it.",
        }[verdict.rule]
        if c.is_token_only:
            results.append(CrawlerResult(c.token, c.operator, c.purpose, home.url, verdict.rule, verdict.matched,
                                         None, None, "inconclusive", cdn,
                                         robots_note + " This is a robots.txt control only; it doesn't fetch pages.",
                                         token_only=True))
            continue
        res = by_token[c.token]
        if isinstance(res, Exception):
            results.append(CrawlerResult(c.token, c.operator, c.purpose, home.url, verdict.rule, verdict.matched,
                                         None, None, "error", cdn, robots_note + f" Our test request failed: {res}"))
            continue
        challenge = detect_challenge(res)
        words = _word_count(page_text(res))
        if baseline_challenge:
            result, note = "inconclusive", "Your site challenged our normal browser request too, so we can't compare."
        elif res.status in (401, 403, 406, 429, 451, 503) or challenge:
            result = "likely_blocked"
            note = (f"Our request with this crawler's name got HTTP {res.status}"
                    + (f" and a {challenge} challenge page" if challenge else "") + ", while a browser got through.")
        elif res.status >= 400:
            result, note = "error", f"Our request with this crawler's name got HTTP {res.status}."
        elif baseline_words >= 100 and words < baseline_words * 0.3:
            result = "likely_blocked"
            note = f"It got a much shorter page ({words} words vs {baseline_words} for a browser)."
        else:
            result, note = "accessible", "Our request with this crawler's name got the normal page."
        results.append(CrawlerResult(c.token, c.operator, c.purpose, home.url, verdict.rule, verdict.matched,
                                     res.status, bool(challenge), result, cdn, robots_note + " " + note))

    blocked_find = [r for r in results if r.purpose in ("search", "user_fetch")
                    and (r.result == "likely_blocked" or r.robots == "disallow")]
    blocked_train = [r for r in results if r.purpose == "training"
                     and (r.result == "likely_blocked" or r.robots == "disallow")]
    evidence = {"cdn": cdn, "baseline_status": home.status, "baseline_words": baseline_words,
                "limitation": "Tests send the crawler's user-agent from our server. Real crawlers come from their "
                              "own IP ranges, which some firewalls treat differently, so a block is 'likely', "
                              "not verified."}
    if blocked_find:
        names = ", ".join(r.token for r in blocked_find)
        where = (" Your site uses Cloudflare: check Security → Bots and 'Block AI bots' / AI Crawl Control."
                 if cdn == "cloudflare" else "")
        check = CheckResult("cdn_waf", "issue",
                            f"Crawlers that help you get found look blocked: {names}.", home.url,
                            evidence_level="likely", evidence=evidence,
                            fix="Allow these crawlers in robots.txt and in your firewall or CDN bot settings." + where)
    elif blocked_train:
        check = CheckResult("cdn_waf", "pass",
                            "Search and answer crawlers can reach your homepage. Some training crawlers are blocked "
                            f"({', '.join(r.token for r in blocked_train)}); that's your choice and doesn't remove "
                            "you from search.", home.url, evidence_level="likely", evidence=evidence)
    else:
        check = CheckResult("cdn_waf", "pass", "All the crawlers we tested can reach your homepage.", home.url,
                            evidence_level="likely", evidence=evidence)
    return results, check


def check_js_render(home: Page, rendered: RenderResult | None, name: str, phones: list[str]) -> CheckResult:
    soup = BeautifulSoup(home.html, "html.parser")
    raw_text = page_text(home, 200_000)
    raw_words = _word_count(raw_text)
    raw_links = len([a for a in soup.find_all("a", href=True) if not a["href"].startswith(("#", "javascript:"))])
    facts = {"name": name, **{f"phone {i + 1}": p for i, p in enumerate(phones[:2])}}
    def present(text: str) -> dict[str, bool]:
        return {k: (_contains_phone(text, v) if k.startswith("phone") else _contains_name(text, v))
                for k, v in facts.items() if v}
    # tel: links are in the HTML crawlers read, so they count as the phone being present.
    tel_links = " ".join(a["href"] for a in soup.find_all("a", href=True) if a["href"].lower().startswith("tel:"))
    raw_facts = present(raw_text + " " + tel_links)
    evidence: dict = {"raw_words": raw_words, "raw_links": raw_links, "raw_facts": raw_facts}
    if rendered is not None:
        evidence |= {"rendered_words": rendered.words, "rendered_links": rendered.links,
                     "rendered_facts": present(rendered.text)}
        missing = [k for k, ok in raw_facts.items() if not ok and evidence["rendered_facts"].get(k)]
        share = raw_words / rendered.words if rendered.words else 1
        if rendered.words >= 50 and share < 0.3:
            return CheckResult("js_render", "issue",
                               f"Most of your homepage text only appears after JavaScript runs "
                               f"({raw_words} words without it, {rendered.words} with it). Most AI crawlers "
                               "don't run JavaScript, so they see a nearly empty page.", home.url,
                               evidence=evidence,
                               fix="Turn on server-side rendering or pre-rendering, or use a site builder that "
                                   "sends the text in the HTML.")
        if missing:
            return CheckResult("js_render", "warning",
                               f"Your {' and '.join(missing)} only appear after JavaScript runs, so most AI "
                               "crawlers won't see them.", home.url, evidence=evidence,
                               fix="Put the business name and phone number in the page HTML (for example the "
                                   "header or footer), not only in scripts.")
        if rendered.links >= 5 and raw_links < rendered.links * 0.3:
            return CheckResult("js_render", "warning",
                               "Your navigation links are built by JavaScript, so crawlers that don't run it "
                               "can't follow them to your other pages.", home.url, evidence=evidence,
                               fix="Use normal <a href> links in the page HTML.")
        return CheckResult("js_render", "pass",
                           "Your homepage text is in the HTML, so crawlers that don't run JavaScript can read it.",
                           home.url, evidence=evidence)
    # No browser available: judge from the raw HTML alone.
    spa_shell = bool(soup.find(id=re.compile(r"^(root|app|__nuxt|__next)$"))) and raw_words < 80
    evidence["rendered"] = False
    if spa_shell:
        return CheckResult("js_render", "issue",
                           f"Your homepage HTML is an empty app shell with only {raw_words} words of text. The "
                           "content is added by JavaScript, which most AI crawlers don't run.", home.url,
                           evidence_level="likely", evidence=evidence,
                           fix="Turn on server-side rendering or pre-rendering.")
    if raw_words < 30:
        return CheckResult("js_render", "warning",
                           f"Your homepage HTML has only {raw_words} words of text. If more is added by "
                           "JavaScript, most AI crawlers won't see it.", home.url, evidence_level="likely",
                           evidence=evidence, fix="Make sure your main text is in the page HTML.")
    if not all(raw_facts.values()):
        missing = [k for k, ok in raw_facts.items() if not ok]
        return CheckResult("js_render", "warning", f"We couldn't find your {' and '.join(missing)} in the homepage HTML.",
                           home.url, evidence_level="likely", evidence=evidence,
                           fix="Put the business name and phone number in the page HTML.")
    return CheckResult("js_render", "pass", "Your homepage text is in the HTML.", home.url, evidence=evidence)


WEBMCP_PATTERN = re.compile(r"modelContext\s*\.\s*(registerTool|provideContext)|navigator\s*\.\s*modelContext")


async def check_webmcp(client: httpx.AsyncClient, home: Page) -> CheckResult:
    soup = BeautifulSoup(home.html, "html.parser")
    found = []
    if WEBMCP_PATTERN.search(home.html):
        found.append(home.url)
    scripts = [urljoin(home.url, s["src"]) for s in soup.find_all("script", src=True)]
    same_site = [u for u in scripts if registrable_domain(u) == registrable_domain(home.url)][:8]
    bodies = await asyncio.gather(*(fetch_page(client, u) for u in same_site), return_exceptions=True)
    found += [u for u, b in zip(same_site, bodies) if isinstance(b, Page) and WEBMCP_PATTERN.search(b.html)]
    evidence = {"scripts_checked": len(same_site) + 1, "found_in": found}
    if found:
        return CheckResult("webmcp", "pass", "Your site offers actions that AI agents can use (WebMCP).",
                           home.url, evidence=evidence)
    return CheckResult("webmcp", "opportunity",
                       "Early opportunity: your site doesn't offer actions AI agents can use yet (WebMCP). "
                       "This is new and experimental, and doesn't affect whether you're found today.",
                       home.url, evidence=evidence,
                       fix="Later, consider exposing 1-3 actions such as 'check delivery to a ZIP code' or 'book "
                           "an appointment'.")


def not_verified_checks(home_url: str) -> list[CheckResult]:
    return [
        CheckResult("google_index", "not_verified",
                    "Not verified yet. Whether Google has indexed your pages needs Google Search Console "
                    "(or search data, coming soon). A 'site:' search is never proof either way.", home_url,
                    evidence_level="observed",
                    fix="Verify your site in Google Search Console, submit your sitemap and inspect your homepage."),
        CheckResult("bing_index", "not_verified",
                    "Not verified yet. Bing's index also feeds Copilot and ChatGPT search; checking it needs Bing "
                    "Webmaster Tools (or search data, coming soon).", home_url,
                    fix="Verify your site in Bing Webmaster Tools (you can import it from Google Search Console) "
                        "and submit your sitemap."),
        CheckResult("indexnow", "not_verified",
                    "Not verified. IndexNow tells Bing and other engines (not Google) when pages change. We can "
                    "only see it in Bing Webmaster Tools or your site's settings.", home_url,
                    fix="If your platform or SEO plugin supports IndexNow, turn it on. Bing Webmaster Tools shows "
                        "recent submissions."),
    ]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


async def run_foundations(url: str, name: str, phones: list[str], client: httpx.AsyncClient | None = None,
                          renderer: Renderer | None = None, site: Site | None = None) -> FoundationReport:
    owns = client is None
    client = client or make_client()
    renderer = renderer if renderer is not None else default_renderer()
    try:
        browser_headers = {"User-Agent": BROWSER_UA, "Accept": "text/html,application/xhtml+xml",
                           "Accept-Language": "en-US,en;q=0.9"}
        if site is None:
            home = await fetch_page(client, normalize_url(url), headers=browser_headers)
            if detect_challenge(home):  # can't crawl further; check what we can
                site = Site(requested_url=url, final_url=home.url, domain=registrable_domain(home.url), pages=[home])
            elif home.status >= 400:
                raise FetchError(f"The website returned HTTP {home.status}.")
            else:
                site = await fetch_site(home.url, client)
                site.pages[0] = home
        home = site.homepage
        robots_url = urljoin(home.url, "/robots.txt")
        http_url = "http://" + urlsplit(home.url).netloc + "/"

        robots_page, http_probe, rendered = await asyncio.gather(
            fetch_page(client, robots_url), fetch_page(client, http_url),
            renderer.render(home.url) if renderer else _none(), return_exceptions=True)
        if isinstance(rendered, Exception):
            rendered = None
        robots = None
        if isinstance(robots_page, Page) and robots_page.status < 400:
            robots = robots_mod.parse(robots_page.html)

        cdn = detect_cdn(home.headers)
        (crawler_results, cdn_check), sitemap_check, webmcp_check = await asyncio.gather(
            check_crawlers(client, home, robots, cdn), check_sitemap(client, home.url, robots),
            check_webmcp(client, home))

        checks = [
            check_http(home, http_probe),
            check_robots(robots_page, robots, home.url),
            sitemap_check,
            cdn_check,
            check_js_render(home, rendered, name, phones),
            *check_noindex(site.pages),
            *check_canonical(site.pages),
            webmcp_check,
            *not_verified_checks(home.url),
        ]
        return FoundationReport(url=url, final_url=home.url, cdn=cdn, platform=detect_platform(home),
                                checks=checks, crawlers=crawler_results, rendered=rendered is not None)
    finally:
        if owns:
            await client.aclose()


async def _none():
    return None
