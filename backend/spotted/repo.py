"""MongoDB access for business profiles and audits.

Collections (names get MONGO_COLLECTION_PREFIX, "spotted_" by default):
  businesses  one document per business: profile columns, the draft/current profile, and the owner-confirmed
              aliases, locations, services and competitors embedded as arrays
  audits      one document per audit run, with its foundation checks and crawler access results embedded
  crawlers    the crawler registry, keyed by robots.txt token (see crawlers.py)

schema/schema.sql is still the reference data model; these documents follow its tables and column names.
"""

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pymongo import ASCENDING, DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

from .config import settings
from .models import BusinessProfile, StoredProfile


def col(db: AsyncDatabase, name: str):
    return db[f"{settings.mongo_collection_prefix}{name}"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _plain(value):
    """JSON round trip so arbitrary evidence (sets, dataclasses, datetimes) stores cleanly as BSON."""
    return json.loads(json.dumps(value, default=str))


def field_origins(p: BusinessProfile) -> dict:
    """Per-field origin summary for businesses.field_origins: a field is 'extracted' only if all its values are."""
    def summary(values) -> str | None:
        origins = {v.origin for v in values if v is not None}
        if not origins:
            return None
        for o in ("inferred", "extracted", "confirmed"):  # weakest origin wins
            if o in origins:
                return o
    fields = {
        "name": [p.name], "category": [p.category], "description": [p.description],
        "subcategories": p.subcategories, "services": p.services, "locations": p.locations,
        "phones": p.phones, "emails": p.emails, "hours": p.hours, "languages": p.languages,
        "target_customer": [p.target_customer], "differentiators": p.differentiators,
        "competitors": p.suggested_competitors,
    }
    return {k: o for k, vals in fields.items() if (o := summary(vals))}


def _columns(p: BusinessProfile) -> dict:
    return {
        "name": p.name.value,
        "website_url": p.website_url,
        "domain": p.domain,
        "category": p.category.value if p.category else None,
        "subcategories": [f.value for f in p.subcategories],
        "description": p.description.value if p.description else None,
        "differentiators": [f.value for f in p.differentiators],
        "languages": [f.value for f in p.languages],
        "target_customer": p.target_customer.value if p.target_customer else None,
        "phones": [f.value for f in p.phones],
        "emails": [f.value for f in p.emails],
        "hours": [f.value for f in p.hours],
        "social_profiles": [{"platform": s.platform, "url": s.url} for s in p.social_profiles],
        "field_origins": field_origins(p),
        "profile_current": p.model_dump(mode="json"),
    }


async def ensure_indexes(db: AsyncDatabase) -> None:
    """Create the collections' indexes (idempotent; MongoDB creates collections on first use)."""
    await col(db, "businesses").create_index([("domain", ASCENDING)])
    await col(db, "audits").create_index([("business_id", ASCENDING), ("config.kind", ASCENDING),
                                          ("created_at", DESCENDING)])
    # Free-run limit per requester IP (airun.py).
    await col(db, "audits").create_index([("requested_ip", ASCENDING), ("created_at", DESCENDING)], sparse=True)


async def create_draft(db: AsyncDatabase, profile: BusinessProfile, raw: dict) -> UUID:
    business_id = uuid4()
    now = _now()
    doc = {"_id": str(business_id), **_columns(profile), "profile_raw": _plain(raw),
           "aliases": [], "locations": [], "services": [], "competitors": [],
           "confirmed_at": None, "created_at": now, "updated_at": now}
    await col(db, "businesses").insert_one(doc)
    return business_id


async def get_profile(db: AsyncDatabase, business_id: UUID) -> StoredProfile | None:
    doc = await col(db, "businesses").find_one({"_id": str(business_id)},
                                               {"profile_current": 1, "confirmed_at": 1})
    if doc is None or doc.get("profile_current") is None:
        return None
    return StoredProfile(
        business_id=doc["_id"],
        confirmed=doc.get("confirmed_at") is not None,
        profile=BusinessProfile.model_validate(doc["profile_current"]),
    )


def mark_confirmed(p: BusinessProfile) -> BusinessProfile:
    """Everything the owner submits is confirmed; source_url/evidence are kept as the record of where it came from."""
    p = p.model_copy(deep=True)
    for fact in [p.name, p.category, p.description, p.target_customer]:
        if fact is not None:
            fact.origin = "confirmed"
    for group in [p.aliases, p.subcategories, p.services, p.locations, p.phones, p.emails, p.hours,
                  p.languages, p.differentiators, p.social_profiles, p.suggested_competitors]:
        for item in group:
            item.origin = "confirmed"
    p.warnings = []
    return p


async def confirm_profile(db: AsyncDatabase, business_id: UUID, submitted: BusinessProfile) -> StoredProfile | None:
    """Store the owner's confirmed profile: business fields plus the embedded aliases, locations, services, competitors."""
    businesses = col(db, "businesses")
    existing = await businesses.find_one({"_id": str(business_id)}, {"competitors": 1})
    if existing is None:
        return None
    p = mark_confirmed(submitted)
    fields = _columns(p)
    # website_url/domain come from the crawl and are not owner-editable here.
    for fixed in ("website_url", "domain"):
        fields.pop(fixed)

    aliases = sorted({a.value.strip() for a in p.aliases if a.value.strip()} - {p.name.value.strip()})
    locations = [
        {"label": loc.label, "address": loc.address, "city": loc.city, "region": loc.region,
         "country_code": loc.country_code, "postal_code": loc.postal_code, "lat": loc.lat, "lng": loc.lng,
         "is_physical": loc.is_physical, "is_target": loc.is_target, "priority": loc.priority, "origin": "confirmed"}
        for loc in p.locations
    ]
    services = [{"name": s.value, "description": s.description, "origin": "confirmed"} for s in p.services]
    # Owner-entered competitors replace earlier suggested/user ones; competitors found other ways are kept.
    user_comps = list(dict.fromkeys(c.value.strip() for c in p.suggested_competitors if c.value.strip()))
    kept = [c for c in existing.get("competitors", [])
            if c.get("origin") not in ("suggested", "user") and c.get("name") not in user_comps]
    competitors = kept + [{"name": c, "origin": "user"} for c in user_comps]

    now = _now()
    await businesses.update_one(
        {"_id": str(business_id)},
        {"$set": {**fields, "aliases": aliases, "locations": locations, "services": services,
                  "competitors": competitors, "confirmed_at": now, "updated_at": now}},
    )
    return await get_profile(db, business_id)


# ---------------------------------------------------------------------------
# Foundation checks (stored as an audit document)
# ---------------------------------------------------------------------------


async def save_foundations(db: AsyncDatabase, business_id: UUID, report, started_at) -> UUID:
    from .foundations import METHODOLOGY_VERSION

    audit_id = uuid4()
    now = _now()
    await col(db, "audits").insert_one({
        "_id": str(audit_id),
        "business_id": str(business_id),
        "tier": "free",
        "status": "complete",
        "methodology_version": METHODOLOGY_VERSION,
        "config": {"kind": "foundations", "url": report.url, "final_url": report.final_url, "cdn": report.cdn,
                   "platform": report.platform, "rendered": report.rendered},
        "started_at": started_at,
        "first_results_at": now,
        "finished_at": now,
        "created_at": now,
        "checks": [
            {"check_type": c.check_type, "target": c.target, "status": c.status,
             "evidence_level": c.evidence_level, "summary": c.summary, "fix": c.fix,
             "evidence": _plain(c.evidence), "checked_at": now}
            for c in report.checks
        ],
        "crawler_access": [
            {"url": r.url, "user_agent": r.token, "robots": r.robots, "http_status": r.http_status,
             "challenge": r.challenge, "result": r.result, "cdn": r.cdn,
             "evidence": {"note": r.note, "robots_line": r.robots_line}}
            for r in report.crawlers
        ],
    })
    return audit_id


async def latest_foundations(db: AsyncDatabase, business_id: UUID) -> dict | None:
    """Latest foundations audit for a business, shaped like the API response."""
    from .crawlers import BY_TOKEN

    audit = await col(db, "audits").find_one(
        {"business_id": str(business_id), "config.kind": "foundations"}, sort=[("created_at", DESCENDING)]
    )
    if audit is None:
        return None
    checks = [{k: c.get(k) for k in ("check_type", "target", "status", "evidence_level", "summary", "fix",
                                     "evidence")} for c in audit.get("checks", [])]
    order = list(BY_TOKEN)
    crawlers = []
    rows = sorted(audit.get("crawler_access", []),
                  key=lambda r: order.index(r["user_agent"]) if r["user_agent"] in order else 99)
    for row in rows:
        c = BY_TOKEN.get(row["user_agent"])
        evidence = row.get("evidence") or {}
        crawlers.append({
            "token": row["user_agent"], "operator": c.operator if c else "", "purpose": c.purpose if c else "",
            "url": row["url"], "robots": row["robots"], "robots_line": evidence.get("robots_line"),
            "http_status": row["http_status"], "challenge": row["challenge"], "result": row["result"],
            "cdn": row["cdn"], "note": evidence.get("note", ""),
            "token_only": bool(c and c.is_token_only),
        })
    cfg = audit["config"]
    finished = audit["finished_at"]
    if finished.tzinfo is None:
        finished = finished.replace(tzinfo=timezone.utc)
    return {"audit_id": audit["_id"], "checked_at": finished.isoformat(),
            "url": cfg.get("url"), "final_url": cfg.get("final_url"), "cdn": cfg.get("cdn"),
            "platform": cfg.get("platform"), "rendered": cfg.get("rendered", False),
            "checks": checks, "crawlers": crawlers}
