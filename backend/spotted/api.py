"""HTTP API. Build order step 1 (website → draft profile → owner confirms) and step 2 (foundation checks).

Run:  uvicorn spotted.api:app --reload   (from backend/)
Docs: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from . import repo
from .config import settings
from .crawl import FetchError
from .crawlers import PURPOSE_LABELS, seed_crawlers
from .foundations import run_foundations
from .llm import LLMError, ProfileLLM, default_llm
from .models import BusinessProfile, ExtractRequest, StoredProfile
from .profile import extract_profile


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = AsyncConnectionPool(settings.database_url, min_size=1, max_size=10, open=False)
    await pool.open()
    async with pool.connection() as conn:
        await repo.apply_schema(conn)
        await seed_crawlers(conn)
    app.state.pool = pool
    yield
    await pool.close()


app = FastAPI(title="Spotted API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"],
                   allow_headers=["*"])


class FoundationsOut(BaseModel):
    audit_id: str
    checked_at: str
    url: str | None
    final_url: str | None
    cdn: str | None
    platform: str | None
    rendered: bool
    checks: list[dict[str, Any]]
    crawlers: list[dict[str, Any]]
    purpose_labels: dict[str, str] = PURPOSE_LABELS


async def get_conn(request: Request):
    async with request.app.state.pool.connection() as conn:
        yield conn


def get_llm() -> ProfileLLM:
    try:
        return default_llm()
    except LLMError as exc:
        raise HTTPException(503, str(exc)) from None


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@app.post("/api/profiles", status_code=201, response_model=StoredProfile)
async def create_profile(
    body: ExtractRequest,
    conn: AsyncConnection = Depends(get_conn),
    llm: ProfileLLM = Depends(get_llm),
) -> StoredProfile:
    """Fetch the website, extract a draft profile and save it unconfirmed."""
    try:
        profile, raw = await extract_profile(body.url, llm)
    except FetchError as exc:
        raise HTTPException(422, str(exc)) from None
    except LLMError as exc:
        raise HTTPException(502, str(exc)) from None
    business_id = await repo.create_draft(conn, profile, raw)
    return StoredProfile(business_id=str(business_id), confirmed=False, profile=profile)


@app.get("/api/businesses/{business_id}", response_model=StoredProfile)
async def read_profile(business_id: UUID, conn: AsyncConnection = Depends(get_conn)) -> StoredProfile:
    stored = await repo.get_profile(conn, business_id)
    if stored is None:
        raise HTTPException(404, "Business not found.")
    return stored


@app.put("/api/businesses/{business_id}/profile", response_model=StoredProfile)
async def confirm_profile(
    business_id: UUID, profile: BusinessProfile, conn: AsyncConnection = Depends(get_conn)
) -> StoredProfile:
    """The owner confirms the (possibly edited) profile. Every submitted value becomes 'confirmed'."""
    if not profile.name.value.strip():
        raise HTTPException(422, "The business name can't be empty.")
    missing = [loc.label or loc.city or loc.address or "a location" for loc in profile.locations if not loc.country_code]
    if missing:
        raise HTTPException(422, f"Add a country for: {', '.join(missing)}.")
    if not any(loc.is_target for loc in profile.locations):
        raise HTTPException(422, "Add at least one place where you want customers to find you.")
    stored = await repo.confirm_profile(conn, business_id, profile)
    if stored is None:
        raise HTTPException(404, "Business not found.")
    return stored


@app.post("/api/businesses/{business_id}/foundations", status_code=201, response_model=FoundationsOut)
async def create_foundations(business_id: UUID, conn: AsyncConnection = Depends(get_conn)) -> FoundationsOut:
    """Run the foundation checks (no AI calls) for a business's website and store them as an audit."""
    stored = await repo.get_profile(conn, business_id)
    if stored is None:
        raise HTTPException(404, "Business not found.")
    p = stored.profile
    started = datetime.now(timezone.utc)
    try:
        report = await run_foundations(p.website_url, p.name.value, [f.value for f in p.phones])
    except FetchError as exc:
        raise HTTPException(422, str(exc)) from None
    await repo.save_foundations(conn, business_id, report, started)
    return FoundationsOut(**await repo.latest_foundations(conn, business_id))


@app.get("/api/businesses/{business_id}/foundations", response_model=FoundationsOut)
async def read_foundations(business_id: UUID, conn: AsyncConnection = Depends(get_conn)) -> FoundationsOut:
    out = await repo.latest_foundations(conn, business_id)
    if out is None:
        raise HTTPException(404, "No foundation checks yet.")
    return FoundationsOut(**out)
