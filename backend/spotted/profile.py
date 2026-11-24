"""Build a draft BusinessProfile from a fetched site: structured facts first, then one LLM call.

Rules (plan section 2): keep extracted and inferred apart, never silently assume service areas,
and give the owner a plain list of what to check.
"""

import json
import re

from .crawl import Site, fetch_site
from .extract import StructuredFacts, extract_structured, page_text
from .llm import ProfileLLM
from .models import (
    BusinessProfile,
    Fact,
    LLMItem,
    LLMLocation,
    LLMProfile,
    Location,
    Service,
    SocialProfile,
)

SYSTEM_PROMPT = """You extract a small business's profile from its own website text.

Rules:
- Use only the pages given. Set stated_on_site=true only when the text says it directly, and copy an
  exact short quote from that page into evidence_quote with the page index.
- Anything you conclude without a direct statement (e.g. the category from the products sold) is
  stated_on_site=false with no quote.
- Locations: include a service area only if the site names it. Never invent a city, address or
  service area. Use ISO 3166-1 alpha-2 country codes; leave country_code empty if the site does not
  make the country clear.
- Services: the concrete products or services offered, short names (2-6 words).
- category: a plain everyday business category a customer would search for (e.g. "florist",
  "family dentist", "interior designer").
- suggested_competitors: up to 5 businesses you know of that compete in the same area and category.
  Leave empty if unsure. These are suggestions for the owner to edit, not facts.
- notes: short, plain-language points the owner should check (missing address, unclear country...).
"""

_WS = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def _norm(text: str) -> str:
    return _NON_ALNUM.sub(" ", text.lower()).strip()


def build_prompt(site: Site, facts: StructuredFacts, texts: list[str]) -> str:
    pages = "\n\n".join(f"### Page {i}: {p.url}\n{t}" for i, (p, t) in enumerate(zip(site.pages, texts)))
    hints = json.dumps(facts.to_hints(), ensure_ascii=False)
    return (
        f"Website: {site.final_url}\n\n"
        f"Structured data found in the page markup (already verified):\n{hints}\n\n"
        f"Page text:\n{pages}"
    )


class _Verifier:
    """Checks an LLM evidence quote against the page text it claims to come from."""

    def __init__(self, site: Site, texts: list[str]):
        self.urls = [p.url for p in site.pages]
        self.norm_texts = [_norm(t) for t in texts]

    def check(self, stated: bool, quote: str | None, page: int | None) -> tuple[str, str | None, str | None]:
        """Return (origin, source_url, evidence)."""
        if not stated or not quote:
            return "inferred", None, None
        q = _norm(quote)
        if len(q) < 3:
            return "inferred", None, None
        order = ([page] if page is not None and 0 <= page < len(self.urls) else []) + list(range(len(self.urls)))
        for i in order:
            if q in self.norm_texts[i]:
                return "extracted", self.urls[i], _WS.sub(" ", quote).strip()[:300]
        return "inferred", None, None

    def fact(self, item: LLMItem) -> Fact:
        origin, url, evidence = self.check(item.stated_on_site, item.evidence_quote, item.page)
        return Fact(value=item.value.strip(), origin=origin, source_url=url, evidence=evidence)


def _dedupe(facts: list, key=lambda f: _norm(f.value)) -> list:
    """Keep the first of each value; an extracted copy wins over an inferred one."""
    best: dict[str, object] = {}
    for f in facts:
        k = key(f)
        if not k:
            continue
        if k not in best or (best[k].origin != "extracted" and f.origin == "extracted"):
            best[k] = f
    return list(best.values())


def _location_from_llm(loc: LLMLocation, v: _Verifier) -> Location | None:
    origin, url, evidence = v.check(loc.stated_on_site, loc.evidence_quote, loc.page)
    if not any([loc.address, loc.city, loc.region, loc.postal_code]):
        return None
    try:
        country = loc.country_code if loc.country_code and len(loc.country_code.strip()) == 2 else None
        return Location(
            label=loc.label,
            address=loc.address,
            city=loc.city,
            region=loc.region,
            country_code=country,
            postal_code=loc.postal_code,
            is_physical=loc.is_physical,
            origin=origin,
            source_url=url,
            evidence=evidence,
        )
    except ValueError:
        return None


def _location_key(loc: Location) -> str:
    if loc.address:
        # Street number + first word of the street is enough to spot duplicates.
        return "addr:" + " ".join(_norm(loc.address).split()[:2])
    return "area:" + _norm(" ".join(filter(None, [loc.city, loc.region, loc.postal_code])))


def merge_profile(site: Site, facts: StructuredFacts, llm: LLMProfile, texts: list[str]) -> BusinessProfile:
    v = _Verifier(site, texts)
    warnings: list[str] = []

    # Name: markup wins over the LLM's reading.
    if facts.names:
        value, src = facts.names[0]
        name = Fact(value=value, origin="extracted", source_url=src)
    else:
        name = v.fact(llm.name)
    llm_names = [llm.name] if facts.names else []  # the LLM's reading of the name, when markup gave one
    aliases = _dedupe(
        [Fact(value=n, origin="extracted", source_url=s) for n, s in facts.names[1:]]
        + [v.fact(a) for a in llm_names + llm.aliases]
    )
    aliases = [a for a in aliases if _norm(a.value) != _norm(name.value)]

    if facts.descriptions:
        d, src = facts.descriptions[0]
        description = Fact(value=d, origin="extracted", source_url=src)
    else:
        description = v.fact(llm.description) if llm.description else None

    services = _dedupe(
        [
            Service(**v.fact(s).model_dump(), description=s.description)
            for s in llm.services
            if s.value.strip()
        ]
    )

    # Locations: schema.org addresses are extracted; LLM ones are verified against page text.
    locations: list[Location] = []
    for addr, src in facts.addresses:
        try:
            locations.append(
                Location(
                    label=None,
                    address=addr.get("street"),
                    city=addr.get("city"),
                    region=addr.get("region"),
                    country_code=_country_code(addr.get("country")),
                    postal_code=addr.get("postal_code"),
                    lat=addr.get("lat"),
                    lng=addr.get("lng"),
                    is_physical=True,
                    origin="extracted",
                    source_url=src,
                )
            )
        except ValueError:
            continue
    for area, src in facts.service_areas:
        locations.append(Location(label=f"Service area: {area}", city=area, is_physical=False,
                                  origin="extracted", source_url=src))
    for loc in llm.locations:
        if (parsed := _location_from_llm(loc, v)) is not None:
            locations.append(parsed)
    seen: dict[str, Location] = {}
    for loc in locations:
        k = _location_key(loc)
        if k in ("addr:", "area:"):
            continue
        prev = seen.get(k)
        if prev is None:
            seen[k] = loc
        else:  # fill gaps in the first copy from later copies
            for fld in ("label", "city", "region", "country_code", "postal_code", "lat", "lng"):
                if getattr(prev, fld) is None and getattr(loc, fld) is not None:
                    setattr(prev, fld, getattr(loc, fld))
    locations = list(seen.values())

    phones = _dedupe([Fact(value=p, origin="extracted", source_url=s) for p, s in facts.phones],
                     key=lambda f: re.sub(r"\D", "", f.value)[-10:])
    emails = _dedupe([Fact(value=e.lower(), origin="extracted", source_url=s) for e, s in facts.emails])
    hours = _dedupe([Fact(value=h, origin="extracted", source_url=s) for h, s in facts.hours])
    languages = _dedupe(
        [Fact(value=lang, origin="extracted", source_url=s) for lang, s in facts.languages]
        + [v.fact(lang) for lang in llm.languages]
    )
    social = []
    seen_social = set()
    for platform, url, src in facts.social:
        key = url.rstrip("/").lower()
        if key not in seen_social:
            seen_social.add(key)
            social.append(SocialProfile(platform=platform, url=url, source_url=src))

    own_names = {_norm(name.value)} | {_norm(a.value) for a in aliases}
    competitors = _dedupe(
        [Fact(value=c.strip(), origin="inferred") for c in llm.suggested_competitors
         if c.strip() and _norm(c) not in own_names]
    )[:5]

    if not any(loc.is_physical and loc.address for loc in locations):
        warnings.append("We couldn't find a street address on the website. Add one if customers can visit you.")
    if not any(not loc.is_physical for loc in locations):
        warnings.append("The website doesn't list service areas. Tell us where you want customers to find you.")
    if any(loc.country_code is None for loc in locations):
        warnings.append("Some locations are missing a country. Please add it.")
    if not phones:
        warnings.append("No phone number found on the website.")
    inferred = [label for label, f in [("business name", name), ("category", llm.category and v.fact(llm.category))]
                if f and f.origin == "inferred"]
    if inferred:
        warnings.append(f"We guessed the {' and '.join(inferred)}. Please check.")
    if competitors:
        warnings.append("Suggested competitors come from AI knowledge and may be out of date. Edit the list.")
    warnings += [n.strip() for n in llm.notes if n.strip()][:5]

    return BusinessProfile(
        website_url=site.final_url,
        domain=site.domain,
        name=name,
        aliases=aliases,
        category=v.fact(llm.category) if llm.category else None,
        subcategories=_dedupe([v.fact(s) for s in llm.subcategories]),
        description=description,
        services=services,
        locations=locations,
        phones=phones,
        emails=emails,
        hours=hours,
        languages=languages,
        target_customer=v.fact(llm.target_customer) if llm.target_customer else None,
        differentiators=_dedupe([v.fact(d) for d in llm.differentiators]),
        social_profiles=social,
        suggested_competitors=competitors,
        warnings=warnings,
        pages_read=[p.url for p in site.pages],
    )


_COUNTRY_NAMES = {"united states": "US", "usa": "US", "united states of america": "US", "india": "IN",
                  "united kingdom": "GB", "uk": "GB", "canada": "CA", "australia": "AU"}


def _country_code(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip()
    if len(v) == 2 and v.isalpha():
        return v.upper()
    return _COUNTRY_NAMES.get(v.lower())


async def extract_profile(url: str, llm: ProfileLLM, site: Site | None = None) -> tuple[BusinessProfile, dict]:
    """Fetch the site and build a draft profile. Returns (profile, raw) where raw is kept for the record."""
    site = site or await fetch_site(url)
    facts = extract_structured(site.pages)
    # Homepage gets more room; key pages less, to keep the prompt small and fast.
    texts = [page_text(p, 12_000 if i == 0 else 6_000) for i, p in enumerate(site.pages)]
    llm_profile = await llm.extract_profile(SYSTEM_PROMPT, build_prompt(site, facts, texts))
    profile = merge_profile(site, facts, llm_profile, texts)
    raw = {
        "model": getattr(llm, "model", None),
        "pages": profile.pages_read,
        "structured": facts.to_hints(),
        "llm": llm_profile.model_dump(),
        "profile": profile.model_dump(),
    }
    return profile, raw
