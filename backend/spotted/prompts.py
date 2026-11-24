"""Customer-style prompts generated from a confirmed profile (plan section 4, prompt taxonomy).

The free run uses a short set (5-10 prompts) that the owner can edit before running. Prompts name the
target city because API answers otherwise follow the server's location (plan section 31, finding 1).
Branded prompts are kept apart: they always mention the business, so they measure accuracy, not visibility.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field

from .models import BusinessProfile

Intent = Literal["discovery", "service", "problem", "budget", "attribute", "neighborhood", "comparison",
                 "branded", "accuracy", "voice_style"]

FREE_RUN_MAX = 10


class PromptIn(BaseModel):
    text: str = Field(min_length=3, max_length=300)
    intent: Intent = "discovery"
    user_edited: bool = False


def plural(noun: str) -> str:
    """'florist' -> 'florists', 'bakery' -> 'bakeries', 'coach' -> 'coaches'; multi-word: last word only."""
    words = noun.strip().split()
    if not words:
        return noun
    w = words[-1]
    low = w.lower()
    if low.endswith(("s", "x", "z", "ch", "sh")):
        w += "es" if not low.endswith("s") else ""
    elif low.endswith("y") and len(low) > 1 and low[-2] not in "aeiou":
        w = w[:-1] + "ies"
    else:
        w += "s"
    return " ".join(words[:-1] + [w])


def target_city(p: BusinessProfile) -> str | None:
    targets = sorted((loc for loc in p.locations if loc.is_target), key=lambda loc: loc.priority)
    for loc in targets or p.locations:
        if loc.city:
            return loc.city
    return None


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().rstrip(".")


def suggest_prompts(p: BusinessProfile, limit: int = 8) -> list[PromptIn]:
    """A short, de-duplicated prompt set for the free run, in priority order."""
    city = target_city(p)
    where = f" in {city}" if city else ""
    category = _clean(p.category.value).lower() if p.category else None
    name = p.name.value.strip()
    out: list[PromptIn] = []

    def add(text: str, intent: Intent):
        text = _clean(text)
        if text and text.lower() not in {x.text.lower() for x in out}:
            out.append(PromptIn(text=text, intent=intent))

    if category:
        add(f"best {plural(category)}{where}", "discovery")
        add(f"recommend a good {category}{where}", "discovery")
    for s in p.services[:3]:
        service = _clean(s.value).lower()
        if category and category in service:
            add(f"{service}{where}", "service")
        else:
            add(f"who offers {service}{where}?", "service")
    for d in p.differentiators[:1]:
        if category:
            add(f"{category}{where} known for {_clean(d.value).lower()}", "attribute")
    if category:
        add(f"affordable {category}{where}", "budget")
    add(f"what is {name}{where} and is it any good?", "branded")
    return out[:limit]


# ---------- full (paid) audit: the whole taxonomy (plan sections 4 and 24) ----------

# Bump when the generated wording, the intents or the caps change, so audits stay comparable.
PROMPTS_VERSION = 2
PAID_CORE_MAX = 25  # core prompts: asked 3 times on every platform, search on and off (plan 24)
PAID_BRANDED_MAX = 5  # branded/accuracy prompts: asked once (facts change less)
BRANDED_INTENTS = ("branded", "accuracy")
CORE_ORDER: tuple[str, ...] = ("discovery", "service", "problem", "budget", "attribute", "neighborhood", "comparison")


def _primary_target(p: BusinessProfile):
    targets = sorted((loc for loc in p.locations if loc.is_target), key=lambda loc: loc.priority)
    return next((loc for loc in targets or p.locations if loc.city), None)


def full_audit_prompts(p: BusinessProfile) -> list[PromptIn]:
    """Up to 25 core prompts across the customer intents, then up to 5 branded/accuracy prompts.

    Intents are interleaved (one of each in turn) so the cap keeps the mix rather than cutting whole intents.
    Every prompt names the target city; the audit swaps it for each extra target location.
    """
    loc = _primary_target(p)
    city = loc.city if loc else None
    where = f" in {city}" if city else ""
    category = _clean(p.category.value).lower() if p.category else None
    cats = plural(category) if category else None
    name = p.name.value.strip()
    services = [_clean(s.value).lower() for s in p.services[:5] if _clean(s.value)]
    diffs = [_clean(d.value).lower() for d in p.differentiators[:3] if _clean(d.value)]
    customer = _clean(p.target_customer.value).lower() if p.target_customer and p.target_customer.value else None
    buckets: dict[str, list[str]] = {k: [] for k in CORE_ORDER + BRANDED_INTENTS}

    def svc(s: str) -> str:
        return f"{s}{where}" if category and category in s else f"who offers {s}{where}?"

    if category:
        buckets["discovery"] += [f"best {cats}{where}", f"recommend a good {category}{where}",
                                 f"top-rated {cats}{where}", f"which {category}{where} do locals trust most?"]
        buckets["budget"] += [f"affordable {category}{where}"]
        buckets["attribute"] += [f"{category}{where} with the best reviews"]
        buckets["comparison"] += [f"compare the top {cats}{where}"]
        if customer:
            buckets["comparison"].append(f"which {category}{where} is best for {customer}?")
        if loc and loc.postal_code:
            buckets["neighborhood"].append(f"best {category} near {loc.postal_code}")
        if city:
            buckets["neighborhood"] += [f"{category} near downtown {city}", f"which {cats} serve {city} and nearby areas?"]
    for s in services:
        buckets["service"].append(svc(s))
        buckets["problem"].append(f"I need {s}{where}. Who should I contact?")
    for s in services[:2]:
        buckets["service"].append(f"best company for {s}{where}")
        buckets["budget"].append(f"good value {s}{where}")
    if not category and services:
        buckets["discovery"].append(f"recommend a business for {services[0]}{where}")
    for d in diffs:
        if category:
            buckets["attribute"].append(f"{category}{where} known for {d}")
    buckets["branded"] += [f"what is {name}{where} and is it any good?", f"what do customers say about {name}{where}?"]
    if services:
        buckets["branded"].append(f"is {name} a good option for {services[0]}{where}?")
    buckets["accuracy"] += [f"what are the address, phone number and opening hours of {name}{where}?",
                            f"what services does {name}{where} offer?"]

    out: list[PromptIn] = []
    seen: set[str] = set()

    def add(text: str, intent: str) -> bool:
        text = _clean(text)
        key = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
        if not text or key in seen:
            return False
        seen.add(key)
        out.append(PromptIn(text=text[:300], intent=intent))
        return True

    core = 0
    queues = {k: list(v) for k, v in buckets.items() if k in CORE_ORDER}
    while core < PAID_CORE_MAX and any(queues.values()):
        for intent in CORE_ORDER:
            if queues[intent] and core < PAID_CORE_MAX and add(queues[intent].pop(0), intent):
                core += 1
    branded = 0
    for intent in BRANDED_INTENTS:  # branded first, then accuracy; capped together
        for text in buckets[intent]:
            if branded < PAID_BRANDED_MAX and add(text, intent):
                branded += 1
    return out


def for_location(text: str, primary: dict, target: dict) -> str:
    """The prompt as asked for another target location: the primary city (and postcode) swapped for its own."""
    old, new = (primary or {}).get("city"), (target or {}).get("city")
    if not new or (old or "").lower() == new.lower():
        return text
    pc = primary.get("postal_code")
    if pc and re.search(rf"\b{re.escape(pc)}\b", text):
        text = re.sub(rf"\b{re.escape(pc)}\b", target.get("postal_code") or new, text)
        if not (old and re.search(rf"\b{re.escape(old)}\b", text, flags=re.IGNORECASE)):
            return text
    if old and re.search(rf"\b{re.escape(old)}\b", text, flags=re.IGNORECASE):
        return re.sub(rf"\b{re.escape(old)}\b", new, text, flags=re.IGNORECASE)
    if re.search(rf"\b{re.escape(new)}\b", text, flags=re.IGNORECASE):
        return text
    return f"{text.rstrip('?').rstrip()} in {new}" + ("?" if text.rstrip().endswith("?") else "")
