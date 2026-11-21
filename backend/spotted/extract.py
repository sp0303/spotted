"""Deterministic extraction: facts the website states in machine-readable form.

Everything here has origin "extracted" and carries the URL it was found on. The LLM step
(profile_llm.py) fills in the rest and is checked against the page text.
"""

import json
import re
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

from .crawl import Page

SOCIAL_HOSTS = {
    "facebook.com": "facebook",
    "instagram.com": "instagram",
    "linkedin.com": "linkedin",
    "x.com": "x",
    "twitter.com": "x",
    "youtube.com": "youtube",
    "tiktok.com": "tiktok",
    "pinterest.com": "pinterest",
    "yelp.com": "yelp",
    "tripadvisor.com": "tripadvisor",
    "nextdoor.com": "nextdoor",
    "g.page": "google_business_profile",
    "maps.app.goo.gl": "google_maps",
    "business.google.com": "google_business_profile",
}

# schema.org types that describe a business (LocalBusiness has hundreds of subtypes; match by suffix too).
BUSINESS_TYPES = re.compile(
    r"(LocalBusiness|Organization|Corporation|Store|Shop|Restaurant|Florist|Dentist|Clinic|Physician|"
    r"Attorney|LegalService|Hotel|Salon|Spa|Agency|Service|Contractor|Plumber|Electrician|Locksmith|"
    r"Bakery|Cafe|CafeOrCoffeeShop|BarOrPub|AutoRepair|RealEstateAgent|MedicalBusiness|HealthClub)$"
)


@dataclass
class StructuredFacts:
    """Facts found in markup. Each list item is (value, source_url)."""

    names: list[tuple[str, str]] = field(default_factory=list)
    schema_types: list[tuple[str, str]] = field(default_factory=list)
    descriptions: list[tuple[str, str]] = field(default_factory=list)
    phones: list[tuple[str, str]] = field(default_factory=list)
    emails: list[tuple[str, str]] = field(default_factory=list)
    addresses: list[tuple[dict, str]] = field(default_factory=list)  # schema.org PostalAddress-like + geo
    hours: list[tuple[str, str]] = field(default_factory=list)
    social: list[tuple[str, str, str]] = field(default_factory=list)  # (platform, url, source_url)
    languages: list[tuple[str, str]] = field(default_factory=list)
    service_areas: list[tuple[str, str]] = field(default_factory=list)

    def to_hints(self) -> dict:
        """Compact JSON for the LLM prompt."""
        return {
            "names": _uniq(v for v, _ in self.names),
            "schema_types": _uniq(v for v, _ in self.schema_types),
            "phones": _uniq(v for v, _ in self.phones),
            "emails": _uniq(v for v, _ in self.emails),
            "addresses": [a for a, _ in self.addresses],
            "hours": _uniq(v for v, _ in self.hours),
            "service_areas": _uniq(v for v, _ in self.service_areas),
            "languages": _uniq(v for v, _ in self.languages),
        }


def _uniq(values) -> list:
    seen, out = set(), []
    for v in values:
        key = v.lower() if isinstance(v, str) else json.dumps(v, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(v)
    return out


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _text(value) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        return _text(value.get("name") or value.get("@value"))
    return None


def _iter_jsonld_nodes(soup: BeautifulSoup):
    for tag in soup.find_all("script", type=re.compile(r"application/ld\+json", re.I)):
        raw = tag.string or tag.get_text()
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        stack = _as_list(data)
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                yield node
                stack.extend(_as_list(node.get("@graph")))
                for key in ("mainEntity", "publisher", "provider", "brand", "author", "location", "department"):
                    if isinstance(node.get(key), (dict, list)):
                        stack.extend(_as_list(node[key]))
            elif isinstance(node, list):
                stack.extend(node)


def _types(node: dict) -> list[str]:
    return [t.rsplit("/", 1)[-1] for t in _as_list(node.get("@type")) if isinstance(t, str)]


def _postal_address(node: dict) -> dict | None:
    addr = node.get("address")
    if isinstance(addr, list):
        addr = addr[0] if addr else None
    if isinstance(addr, str):
        out = {"street": addr}
    elif isinstance(addr, dict):
        country = addr.get("addressCountry")
        out = {
            "street": _text(addr.get("streetAddress")),
            "city": _text(addr.get("addressLocality")),
            "region": _text(addr.get("addressRegion")),
            "postal_code": _text(addr.get("postalCode")),
            "country": _text(country) if not isinstance(country, str) else country.strip(),
        }
    else:
        out = {}
    geo = node.get("geo")
    if isinstance(geo, dict):
        try:
            out["lat"], out["lng"] = float(geo["latitude"]), float(geo["longitude"])
        except (KeyError, TypeError, ValueError):
            pass
    out = {k: v for k, v in out.items() if v not in (None, "")}
    return out or None


def _hours(node: dict) -> list[str]:
    out = [h for h in _as_list(node.get("openingHours")) if isinstance(h, str)]
    for spec in _as_list(node.get("openingHoursSpecification")):
        if not isinstance(spec, dict):
            continue
        days = ",".join(d.rsplit("/", 1)[-1] for d in _as_list(spec.get("dayOfWeek")) if isinstance(d, str))
        if days and spec.get("opens") and spec.get("closes"):
            out.append(f"{days} {spec['opens']}-{spec['closes']}")
    return out


def social_platform(url: str) -> str | None:
    host = (urlsplit(url).hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    for known, platform in SOCIAL_HOSTS.items():
        if host == known or host.endswith("." + known):
            return platform
    if host.startswith("google.") and "/maps" in urlsplit(url).path:
        return "google_maps"
    return None


def extract_structured(pages: list[Page]) -> StructuredFacts:
    facts = StructuredFacts()
    for page in pages:
        soup = BeautifulSoup(page.html, "html.parser")
        src = page.url

        for node in _iter_jsonld_nodes(soup):
            types = _types(node)
            if not any(BUSINESS_TYPES.search(t) for t in types):
                continue
            facts.schema_types += [(t, src) for t in types]
            if name := _text(node.get("name")):
                facts.names.append((name, src))
            if desc := _text(node.get("description")):
                facts.descriptions.append((desc, src))
            facts.phones += [(p.strip(), src) for p in _as_list(node.get("telephone")) if isinstance(p, str)]
            facts.emails += [
                (e.removeprefix("mailto:").strip(), src) for e in _as_list(node.get("email")) if isinstance(e, str)
            ]
            if addr := _postal_address(node):
                facts.addresses.append((addr, src))
            facts.hours += [(h, src) for h in _hours(node)]
            for area in _as_list(node.get("areaServed")):
                if a := _text(area):
                    facts.service_areas.append((a, src))
            for link in _as_list(node.get("sameAs")):
                if isinstance(link, str) and (platform := social_platform(link)):
                    facts.social.append((platform, link, src))

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.lower().startswith("tel:"):
                number = unquote(href[4:]).strip()
                if sum(c.isdigit() for c in number) >= 7:
                    facts.phones.append((number, src))
            elif href.lower().startswith("mailto:"):
                email = unquote(href[7:]).split("?")[0].strip()
                if "@" in email:
                    facts.emails.append((email, src))
            elif href.startswith("http") and (platform := social_platform(href)):
                facts.social.append((platform, href, src))

        if (html := soup.find("html")) and html.get("lang"):
            facts.languages.append((html["lang"].split("-")[0].lower(), src))
        for link in soup.find_all("link", rel="alternate", hreflang=True):
            lang = link["hreflang"].split("-")[0].lower()
            if lang != "x":
                facts.languages.append((lang, src))

        if page is pages[0]:
            og = soup.find("meta", property="og:site_name")
            if og and og.get("content", "").strip():
                facts.names.append((og["content"].strip(), src))
            meta = soup.find("meta", attrs={"name": "description"})
            if meta and meta.get("content", "").strip():
                facts.descriptions.append((meta["content"].strip(), src))
    return facts


def page_text(page: Page, max_chars: int = 12_000) -> str:
    """Visible text of a page, scripts and styles removed, whitespace collapsed."""
    soup = BeautifulSoup(page.html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "template", "iframe"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    body = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", f"{title}\n{body}").strip()
    return text[:max_chars]
