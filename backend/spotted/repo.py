"""Postgres access for business profiles (tables in schema/schema.sql)."""

import json
from pathlib import Path
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .models import BusinessProfile, StoredProfile

SCHEMA_FILE = Path(__file__).resolve().parents[2] / "schema" / "schema.sql"


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
        "social_profiles": Jsonb([{"platform": s.platform, "url": s.url} for s in p.social_profiles]),
        "field_origins": Jsonb(field_origins(p)),
        "profile_current": Jsonb(p.model_dump(mode="json")),
    }


async def apply_schema(conn: AsyncConnection) -> None:
    """Create the schema if the businesses table doesn't exist yet (dev convenience, not migrations)."""
    cur = await conn.execute("SELECT to_regclass('public.businesses') IS NOT NULL")
    if not (await cur.fetchone())[0]:
        await conn.execute(SCHEMA_FILE.read_text())


async def create_draft(conn: AsyncConnection, profile: BusinessProfile, raw: dict) -> UUID:
    cols = _columns(profile) | {"profile_raw": Jsonb(json.loads(json.dumps(raw, default=str)))}
    names = ", ".join(cols)
    params = ", ".join(f"%({k})s" for k in cols)
    cur = await conn.execute(f"INSERT INTO businesses ({names}) VALUES ({params}) RETURNING id", cols)
    return (await cur.fetchone())[0]


async def get_profile(conn: AsyncConnection, business_id: UUID) -> StoredProfile | None:
    cur = conn.cursor(row_factory=dict_row)
    await cur.execute("SELECT id, profile_current, confirmed_at FROM businesses WHERE id = %s", (business_id,))
    row = await cur.fetchone()
    if row is None or row["profile_current"] is None:
        return None
    return StoredProfile(
        business_id=str(row["id"]),
        confirmed=row["confirmed_at"] is not None,
        profile=BusinessProfile.model_validate(row["profile_current"]),
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


async def confirm_profile(conn: AsyncConnection, business_id: UUID, submitted: BusinessProfile) -> StoredProfile | None:
    """Store the owner's confirmed profile: business columns plus the normalized child tables."""
    p = mark_confirmed(submitted)
    cols = _columns(p)
    # website_url/domain come from the crawl and are not owner-editable here.
    for fixed in ("website_url", "domain"):
        cols.pop(fixed)
    sets = ", ".join(f"{k} = %({k})s" for k in cols)
    async with conn.transaction():
        cur = await conn.execute(
            f"UPDATE businesses SET {sets}, confirmed_at = now(), updated_at = now() WHERE id = %(id)s RETURNING id",
            cols | {"id": business_id},
        )
        if await cur.fetchone() is None:
            return None
        for table in ("business_aliases", "business_locations", "services"):
            await conn.execute(f"DELETE FROM {table} WHERE business_id = %s", (business_id,))
        await conn.execute("DELETE FROM competitors WHERE business_id = %s AND origin IN ('suggested', 'user')",
                           (business_id,))
        async with conn.cursor() as cur:
            aliases = {a.value.strip() for a in p.aliases if a.value.strip()} - {p.name.value.strip()}
            if aliases:
                await cur.executemany(
                    "INSERT INTO business_aliases (business_id, alias) VALUES (%s, %s)",
                    [(business_id, a) for a in sorted(aliases)],
                )
            if p.locations:
                await cur.executemany(
                    """INSERT INTO business_locations
                       (business_id, label, address, city, region, country_code, postal_code, lat, lng,
                        is_physical, is_target, priority, origin)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'confirmed')""",
                    [(business_id, loc.label, loc.address, loc.city, loc.region, loc.country_code, loc.postal_code,
                      loc.lat, loc.lng, loc.is_physical, loc.is_target, loc.priority) for loc in p.locations],
                )
            if p.services:
                await cur.executemany(
                    "INSERT INTO services (business_id, name, description, origin) VALUES (%s, %s, %s, 'confirmed')",
                    [(business_id, s.value, s.description) for s in p.services],
                )
            comps = list(dict.fromkeys(c.value.strip() for c in p.suggested_competitors if c.value.strip()))
            if comps:
                await cur.executemany(
                    """INSERT INTO competitors (business_id, name, origin) VALUES (%s, %s, 'user')
                       ON CONFLICT (business_id, name) DO UPDATE SET origin = 'user'""",
                    [(business_id, c) for c in comps],
                )
    return await get_profile(conn, business_id)
