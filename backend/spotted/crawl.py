"""Fetch a business website: the homepage plus a few key pages (about, contact, services, locations).

User-submitted URLs are fetched by our server, so every hop (including redirects) is checked
against private, loopback and link-local addresses before it is requested.
"""

import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

from .config import settings

USER_AGENT = "SpottedBot/0.1 (+business visibility audit; profile extraction)"
MAX_REDIRECTS = 5

# Links worth following for a business profile, scored by how useful the page usually is.
KEY_PAGE_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"contact|find-us|visit|directions", re.I), 5),
    (re.compile(r"about|our-story|who-we-are|team", re.I), 4),
    (re.compile(r"location|store|branch|service-area|areas-we-serve|delivery", re.I), 4),
    (re.compile(r"services|what-we-do|products|menu|treatments|pricing|prices", re.I), 3),
    (re.compile(r"faq|hours", re.I), 2),
]


class FetchError(Exception):
    """The site could not be fetched; message is safe to show to the user."""


@dataclass
class Page:
    url: str
    status: int
    html: str
    content_type: str = ""
    headers: dict[str, str] = field(default_factory=dict)  # lower-cased names
    redirects: list[tuple[str, int]] = field(default_factory=list)  # hops before the final URL


@dataclass
class Site:
    requested_url: str
    final_url: str
    domain: str
    pages: list[Page] = field(default_factory=list)

    @property
    def homepage(self) -> Page:
        return self.pages[0]


def normalize_url(raw: str) -> str:
    """Add a scheme if missing, lower-case the host, drop fragments. Raises FetchError when unusable."""
    raw = raw.strip()
    if not raw:
        raise FetchError("Enter a website address.")
    if not re.match(r"^[a-z][a-z0-9+.-]*://", raw, re.I):
        raw = "https://" + raw
    parts = urlsplit(raw)
    if parts.scheme.lower() not in ("http", "https"):
        raise FetchError("Only http and https websites can be checked.")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host or "." not in host:
        raise FetchError("That doesn't look like a website address.")
    netloc = host if parts.port is None else f"{host}:{parts.port}"
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", parts.query, ""))


def registrable_domain(url: str) -> str:
    """Normalized domain for matching: host without a leading 'www.'."""
    host = (urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _is_public_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_global and not addr.is_multicast


async def assert_public_host(host: str) -> None:
    """Raise FetchError unless every address the host resolves to is public."""
    if settings.allow_private_hosts:  # local development against fixture sites only
        return
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise FetchError(f"Couldn't find a website at {host}.") from None
    ips = {info[4][0] for info in infos}
    if not ips or not all(_is_public_ip(ip) for ip in ips):
        raise FetchError(f"{host} isn't a public website.")


async def fetch_page(client: httpx.AsyncClient, url: str, headers: dict[str, str] | None = None) -> Page:
    """GET a URL, following redirects manually so each hop is checked. Body is capped in size."""
    redirects: list[tuple[str, int]] = []
    for _ in range(MAX_REDIRECTS + 1):
        await assert_public_host(urlsplit(url).hostname or "")
        try:
            async with client.stream("GET", url, headers=headers) as resp:
                if resp.is_redirect and "location" in resp.headers:
                    redirects.append((url, resp.status_code))
                    url = normalize_url(urljoin(url, resp.headers["location"]))
                    continue
                chunks, size = [], 0
                async for chunk in resp.aiter_bytes():
                    size += len(chunk)
                    if size > settings.max_page_bytes:
                        break
                    chunks.append(chunk)
                body = b"".join(chunks)
                encoding = resp.charset_encoding or "utf-8"
                return Page(
                    url=str(resp.url),
                    status=resp.status_code,
                    html=body.decode(encoding, errors="replace"),
                    content_type=resp.headers.get("content-type", ""),
                    headers={k.lower(): v for k, v in resp.headers.items()},
                    redirects=redirects,
                )
        except httpx.TimeoutException:
            raise FetchError(f"{urlsplit(url).hostname} took too long to respond.") from None
        except httpx.HTTPError as exc:
            raise FetchError(f"Couldn't load {urlsplit(url).hostname}: {type(exc).__name__}.") from None
    raise FetchError("The website redirected too many times.")


def pick_key_pages(page: Page, limit: int) -> list[str]:
    """Same-site links from the homepage most likely to hold profile facts, best first."""
    soup = BeautifulSoup(page.html, "html.parser")
    home_domain = registrable_domain(page.url)
    scored: dict[str, int] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        try:
            url = normalize_url(urljoin(page.url, href))
        except FetchError:
            continue
        if registrable_domain(url) != home_domain or url.rstrip("/") == page.url.rstrip("/"):
            continue
        if re.search(r"\.(pdf|jpe?g|png|gif|webp|svg|zip|mp4)$", urlsplit(url).path, re.I):
            continue
        haystack = urlsplit(url).path + " " + a.get_text(" ", strip=True)
        score = max((s for pat, s in KEY_PAGE_PATTERNS if pat.search(haystack)), default=0)
        if score:
            scored[url] = max(score, scored.get(url, 0))
    return sorted(scored, key=lambda u: (-scored[u], len(u)))[:limit]


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=settings.fetch_timeout_s,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )


async def fetch_site(raw_url: str, client: httpx.AsyncClient | None = None) -> Site:
    """Fetch the homepage, then the key pages in parallel. Failed extra pages are skipped."""
    url = normalize_url(raw_url)
    owns_client = client is None
    client = client or make_client()
    try:
        home = await fetch_page(client, url)
        if home.status >= 400:
            raise FetchError(f"The website returned HTTP {home.status}.")
        if "html" not in home.content_type.lower() and "<html" not in home.html[:2000].lower():
            raise FetchError("The address didn't return a web page.")
        site = Site(requested_url=url, final_url=home.url, domain=registrable_domain(home.url), pages=[home])

        extra_urls = pick_key_pages(home, settings.max_extra_pages)
        results = await asyncio.gather(*(fetch_page(client, u) for u in extra_urls), return_exceptions=True)
        for res in results:
            if isinstance(res, Page) and res.status < 400 and "html" in res.content_type.lower():
                site.pages.append(res)
        return site
    finally:
        if owns_client:
            await client.aclose()
