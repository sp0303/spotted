"""Map position for a confirmed location, so Google Maps grounding can search from the right place.

Uses OpenStreetMap Nominatim (free; usage policy: identify the app, at most 1 request per second, cache results).
Only the business's public address or city is sent. Best effort: no position just means Maps grounding is skipped.
"""

import asyncio
import time

import httpx

from .models import Location

NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "Spotted/0.1 (AI visibility checks for local businesses)"

_cache: dict[str, tuple[float, float] | None] = {}
_lock = asyncio.Lock()
_last = 0.0


def query_for(loc: Location) -> str | None:
    parts = [loc.address, loc.city, loc.region, loc.postal_code, loc.country_code]
    if not (loc.address or loc.city):
        return None
    return ", ".join(p for p in parts if p)


async def geocode(query: str, timeout_s: float = 6.0) -> tuple[float, float] | None:
    global _last
    key = query.lower().strip()
    if key in _cache:
        return _cache[key]
    async with _lock:  # one request per second across the app
        wait = 1.0 - (time.monotonic() - _last)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            async with httpx.AsyncClient(timeout=timeout_s, headers={"User-Agent": USER_AGENT}) as http:
                r = await http.get(NOMINATIM, params={"q": query, "format": "jsonv2", "limit": 1})
            _last = time.monotonic()
            hits = r.json() if r.status_code == 200 else []
            point = (float(hits[0]["lat"]), float(hits[0]["lon"])) if hits else None
        except (httpx.HTTPError, ValueError, KeyError, IndexError):
            return None  # not cached: try again next time
    _cache[key] = point
    return point


async def fill_positions(locations: list[Location], geocoder=geocode) -> list[Location]:
    """Add lat/lng to target locations that have an address or city but no position. Returns new objects."""
    out = []
    for loc in locations:
        if loc.is_target and (loc.lat is None or loc.lng is None) and (q := query_for(loc)):
            point = await geocoder(q)
            if point is None and loc.address and loc.city:
                # A street the geocoder doesn't know: the city centre still beats no position.
                point = await geocoder(", ".join(p for p in (loc.city, loc.region, loc.country_code) if p))
            if point:
                loc = loc.model_copy(update={"lat": point[0], "lng": point[1]})
        out.append(loc)
    return out
