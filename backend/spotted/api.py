"""HTTP API. Step 1 of the build order: URL in, draft profile out, owner confirms.

Run:  uvicorn spotted.api:app --reload   (from backend/)
Docs: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from . import repo
from .config import settings
from .crawl import FetchError
from .llm import LLMError, ProfileLLM, default_llm
from .models import BusinessProfile, ExtractRequest, StoredProfile
from .profile import extract_profile


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = AsyncConnectionPool(settings.database_url, min_size=1, max_size=10, open=False)
    await pool.open()
    async with pool.connection() as conn:
        await repo.apply_schema(conn)
    app.state.pool = pool
    yield
    await pool.close()


app = FastAPI(title="Spotted API", version="0.1.0", lifespan=lifespan)


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
