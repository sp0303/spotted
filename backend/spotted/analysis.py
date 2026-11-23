"""Reading an AI answer: who was named, was the client recommended, which sources were cited (plan sections 3C-3F).

One structured Gemini call lists the businesses in the answer; matching the client, sorting sources and
checking facts against the confirmed profile are done here in code, so they can be tested and trusted.
"""

import asyncio
import difflib
import re
from typing import Literal, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel

from .config import settings
from .models import BusinessProfile


# ---------- names ----------

GENERIC = {"the", "and", "co", "company", "inc", "llc", "ltd", "of", "by", "on", "at", "&"}


def norm(name: str, category_words: frozenset = frozenset()) -> str:
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower().replace("&", " and ")).split()
    key = " ".join(w for w in words if w not in GENERIC and w not in category_words)
    return key or " ".join(words)


def same_name(a: str, b: str, category_words: frozenset = frozenset()) -> bool:
    a, b = norm(a, category_words), norm(b, category_words)
    if not a or not b:
        return False
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    # "in bloom" inside "in bloom mockingbird" is the same shop; a lone short word ("lane") is not enough.
    distinctive = len(short.split()) >= 2 or (len(short) >= 6 and len(long_.split()) <= 2)
    if distinctive and re.search(rf"\b{re.escape(short)}\b", long_):
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.88


def category_words(p: BusinessProfile) -> frozenset:
    """Words too common to identify a business here ('florist', 'flowers', the city)."""
    words = set()
    if p.category:
        words |= set(re.sub(r"[^a-z ]", " ", p.category.value.lower()).split())
        words |= {w + "s" for w in list(words)} | {w.rstrip("s") for w in list(words)}
    for loc in p.locations:
        if loc.city:
            words |= set(loc.city.lower().split())
    if words & {"florist", "florists"}:
        words |= {"flower", "flowers", "floral", "designs", "design", "events"}
    return frozenset(words)


# ---------- the LLM reading ----------

class NamedBusiness(BaseModel):
    name: str
    kind: Literal["recommended", "mentioned"]
    context: str
    attributes: list[str] = []
    stated_address: str | None = None
    stated_phone: str | None = None
    stated_rating: str | None = None
    is_target_business: bool = False


class AnswerReading(BaseModel):
    businesses: list[NamedBusiness]
    asked_for_location: bool = False


READ_INSTRUCTION = """You read an AI assistant's answer to a customer's question and list the businesses in it.

List every business the answer names, in the order they first appear. Rules:
- kind "recommended": presented as a suggestion or option for the customer. "mentioned": named in passing,
  compared against, or warned about.
- Exclude publications, review sites, directories, apps and marketplaces used as sources or channels
  (Yelp, Google, The Knot, D Magazine, DoorDash, Instacart), unless the answer recommends them as the provider.
- context: the sentence that names it (max 200 characters). attributes: short descriptors the answer gives it
  ("same-day delivery", "luxury", "since 1948"). Copy stated address, phone and rating exactly if given.
- is_target_business: true only for "{name}" ({domain}{aliases}).
- asked_for_location: true if the answer asks where the customer is instead of naming businesses.

ANSWER:
{answer}"""


class Reader(Protocol):
    async def read(self, answer: str, profile: BusinessProfile) -> tuple[AnswerReading, int, int]: ...


class GeminiReader:
    def __init__(self):
        from google import genai

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._sem = asyncio.Semaphore(8)

    async def read(self, answer: str, profile: BusinessProfile) -> tuple[AnswerReading, int, int]:
        from google.genai import types

        aliases = [a.value for a in profile.aliases]
        prompt = READ_INSTRUCTION.format(name=profile.name.value, domain=profile.domain,
                                         aliases=f"; also called {', '.join(aliases)}" if aliases else "",
                                         answer=answer[:12000])
        async with self._sem:
            resp = await asyncio.wait_for(self._client.aio.models.generate_content(
                model=settings.gemini_model, contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json",
                                                   response_schema=AnswerReading, temperature=0)),
                settings.ai_call_timeout_s)
        reading = resp.parsed if isinstance(resp.parsed, AnswerReading) else \
            AnswerReading.model_validate_json(resp.text or '{"businesses": []}')
        m = resp.usage_metadata
        tin = (m.prompt_token_count or 0) if m else 0
        tout = ((m.candidates_token_count or 0) + (getattr(m, "thoughts_token_count", 0) or 0)) if m else 0
        return reading, tin, tout


# ---------- turning a reading into mentions ----------

def digits(s: str | None) -> str:
    d = re.sub(r"\D", "", s or "")
    return d[-10:]


def is_client(name: str, profile: BusinessProfile, cw: frozenset) -> bool:
    return any(same_name(name, n, cw) for n in [profile.name.value] + [a.value for a in profile.aliases])


def wrong_facts(b: NamedBusiness, profile: BusinessProfile) -> dict:
    """Facts the answer states about the client that conflict with the confirmed profile."""
    wrong = {}
    phones = {digits(p.value) for p in profile.phones if digits(p.value)}
    if b.stated_phone and phones and digits(b.stated_phone) and digits(b.stated_phone) not in phones:
        wrong["phone"] = {"said": b.stated_phone, "confirmed": [p.value for p in profile.phones]}
    # Only a street address can be wrong; "Bishop Arts District" or "Dallas" is a looser description, not an error.
    if b.stated_address and re.search(r"\d", b.stated_address):
        said = b.stated_address.lower()
        known = [loc for loc in profile.locations if loc.is_physical and (loc.address or loc.city)]
        if known and not any((loc.address and loc.address.lower().split(",")[0] in said) or
                             (not loc.address and loc.city and loc.city.lower() in said) for loc in known):
            wrong["address"] = {"said": b.stated_address,
                                "confirmed": [", ".join(x for x in (loc.address, loc.city) if x) for loc in known]}
    return wrong


def mentions_from(reading: AnswerReading, profile: BusinessProfile, competitors: list[str]) -> list[dict]:
    cw = category_words(profile)
    out, seen = [], []
    for b in reading.businesses:
        key = norm(b.name, cw)
        if any(same_name(b.name, s, cw) for s in seen):
            continue  # the same business named twice
        seen.append(b.name)
        client = is_client(b.name, profile, cw) or (b.is_target_business and
                                                     difflib.SequenceMatcher(None, key, norm(profile.name.value, cw)).ratio() > 0.5)
        comp = next((c for c in competitors if same_name(b.name, c, cw)), None)
        out.append({
            "entity_name": b.name, "normalized": key, "is_client": client,
            "competitor": None if client else comp, "position": len(out) + 1, "kind": b.kind,
            "context": b.context[:300], "attributes": b.attributes[:8],
            "facts": {k: v for k, v in (("address", b.stated_address), ("phone", b.stated_phone),
                                        ("rating", b.stated_rating)) if v},
            "facts_wrong": wrong_facts(b, profile) if client else {},
        })
    return out


# ---------- sources ----------

SOURCE_TYPES = {
    "directory": ["yelp.", "yellowpages.", "bbb.org", "nextdoor.", "angi.", "thumbtack.", "manta.", "chamberofcommerce.",
                  "mapquest.", "foursquare.", "superpages.", "citysearch.", "expertise.com", "threebestrated.", "bark.com",
                  "magicpin.", "birdeye.", "porch.", "houzz.", "bloomnation.", "chamber", "visitdallas.", "dallasites101."],
    "review_site": ["tripadvisor.", "trustpilot.", "theknot.", "weddingwire.", "zola.", "consumeraffairs.", "sitejabber."],
    "social": ["facebook.", "instagram.", "tiktok.", "twitter.", "x.com", "linkedin.", "pinterest.", "youtube."],
    "forum": ["reddit.", "quora.", "tripadvisor.com/showtopic"],
    "maps": ["google.com/maps", "maps.google.", "maps.apple.", "bing.com/maps", "goo.gl/maps"],
    "marketplace": ["doordash.", "ubereats.", "instacart.", "amazon.", "etsy.", "1800flowers.", "ftd.", "teleflora.",
                    "bloomnation.", "urbanstems.", "proflowers."],
    "publication": ["dmagazine.", "dallasnews.", "timeout.", "eater.", "nytimes.", "forbes.", "culturemap.", "patch.com",
                    "axios.", "texasmonthly.", "guidedallas.", "dallasobserver.", "cbsnews.", "nbcnews.", "abcnews.",
                    "foxnews.", "nbcdfw.", "wfaa.", "fox4news.", "kera.", "papercitymag.", "modernluxury.", "thursd.",
                    "candysdirt.", "advocatemag.", "peoplenewspapers.", "voyagedallas.", "smudailycampus.", "usatoday.",
                    "washingtonpost.", "theguardian.", "bbc.", "latimes.", "chicagotribune.", "buzzfeed.", "refinery29."],
}


def domain_of(url: str | None, title: str | None) -> str:
    host = urlsplit(url or "").hostname or ""
    if not host or "vertexaisearch" in host or "googleusercontent" in host:
        host = (title or "").strip().lower()  # Gemini's grounding title is the source's domain
    host = host.lower().removeprefix("www.")
    return host if "." in host else ""


def source_type(domain: str, url: str, client_domain: str, competitor_names: list[str], cw: frozenset) -> str:
    target = f"{domain}{urlsplit(url or '').path}".lower()
    if client_domain and (domain == client_domain or domain.endswith("." + client_domain)):
        return "own_site"
    for kind, needles in SOURCE_TYPES.items():
        if any(n in target for n in needles):
            return kind
    label = domain.split(".")[0].replace("-", "")
    # Another business in the same trade (e.g. a florist's own shop site), even if the answer didn't name it:
    # it isn't a place to get listed, so it must not become a "get featured here" suggestion.
    if any(len(w) >= 5 and w in label for w in cw):
        return "competitor_site"
    for c in competitor_names:
        key = norm(c, cw).replace(" ", "")
        if len(key) >= 4 and key in label:
            return "competitor_site"
    return "other"


def citations_from(sources: list[dict], profile: BusinessProfile, named: list[str]) -> list[dict]:
    cw = category_words(profile)
    client_domain = profile.domain.lower().removeprefix("www.")
    out, seen = [], set()
    for s in sources:
        d = domain_of(s.get("url"), s.get("title"))
        key = (d, s.get("url"))
        if not d or key in seen:
            continue
        seen.add(key)
        out.append({"url": s.get("url") or f"https://{d}", "domain": d, "title": s.get("title"),
                    "position": len(out) + 1,
                    "source_type": source_type(d, s.get("url") or "", client_domain, named, cw)})
    return out


def retype_citations(audit: dict, profile: BusinessProfile) -> dict:
    """Re-apply the current source-type rules to a stored audit's citations (in place; returns the audit).

    Source typing improves over time (new publications, same-trade sites); stored runs keep the type they were
    saved with, so reports re-type them with today's rules. Own site and same-trade detection need the profile.
    """
    cw = category_words(profile)
    client_domain = profile.domain.lower().removeprefix("www.")
    for run in audit.get("runs", []):
        named = [m["entity_name"] for m in run.get("mentions", [])]
        for c in run.get("citations", []):
            if c.get("domain"):
                c["source_type"] = source_type(c["domain"], c.get("url") or "", client_domain, named, cw)
    return audit
