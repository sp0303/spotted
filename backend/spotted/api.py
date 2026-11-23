"""HTTP API. Build order step 1 (website → draft profile → owner confirms) and step 2 (foundation checks).

Run:  uvicorn spotted.api:app --reload   (from backend/)
Docs: http://localhost:8000/docs
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from . import repo
from .config import settings
from .crawl import FetchError
from .crawlers import PURPOSE_LABELS, seed_crawlers
from .foundations import run_foundations
from .llm import LLMError, ProfileLLM, default_llm
from .models import BusinessProfile, ExtractRequest, StoredProfile
from .profile import extract_profile
from . import airun
from .analysis import GeminiReader, Reader
from .platforms import PLATFORMS, Answerer, LiveAnswerer, available_platforms, coming_soon, default_platforms
from .prompts import (BRANDED_INTENTS, FREE_RUN_MAX, PAID_BRANDED_MAX, PAID_CORE_MAX, PromptIn, full_audit_prompts,
                      suggest_prompts)
from .geocode import fill_positions, geocode


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncMongoClient(settings.mongo_url, tz_aware=True)
    db = client[settings.mongo_db]
    await repo.ensure_indexes(db)
    await seed_crawlers(db)
    await airun.mark_stale_running(db)
    app.state.db = db
    app.state.tasks = set()  # running AI audits (kept referenced so they aren't garbage-collected)
    yield
    await client.close()


app = FastAPI(title="Spotted API", version="0.1.0", lifespan=lifespan)

# Feature routers (build steps 4-6). Each owns its own module; see their docstrings.
from .routes_report import router as report_router  # noqa: E402
from .routes_search import router as search_router  # noqa: E402

app.include_router(report_router)
app.include_router(search_router)
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


from .deps import get_conn  # noqa: E402  (shared with the feature routers)


def get_llm() -> ProfileLLM:
    try:
        return default_llm()
    except LLMError as exc:
        raise HTTPException(503, str(exc)) from None


class PromptsOut(BaseModel):
    prompts: list[PromptIn]
    platforms: list[dict[str, Any]]
    coming_soon: list[dict[str, str]] = []
    max_prompts: int = FREE_RUN_MAX
    # Full ("paid") audit, build step 7: its own longer prompt set and whether it can be started yet.
    full_prompts: list[PromptIn] = []
    full_audit: dict[str, Any] = {}
    free_limits: dict[str, Any] = {}


class AIRunRequest(BaseModel):
    prompts: list[PromptIn]
    platforms: list[str] | None = None
    tier: Literal["free", "paid"] = "free"
    # Full audit only (ignored for the free run): repeat runs, search-off runs, every target location.
    runs: int | None = Field(default=None, ge=1, le=10)
    search_off: bool = True
    all_locations: bool = True


def get_geocoder():
    """Swappable in tests (no network)."""
    return geocode


_answerer: Answerer | None = None
_reader: Reader | None = None


def get_answerer() -> Answerer:
    global _answerer
    if _answerer is None:
        _answerer = LiveAnswerer()
    return _answerer


def get_reader() -> Reader:
    global _reader
    if not settings.gemini_api_key:
        raise HTTPException(503, "GEMINI_API_KEY is not set.")
    if _reader is None:
        _reader = GeminiReader()
    return _reader


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@app.post("/api/profiles", status_code=201, response_model=StoredProfile)
async def create_profile(
    body: ExtractRequest,
    conn: AsyncDatabase = Depends(get_conn),
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
async def read_profile(business_id: UUID, conn: AsyncDatabase = Depends(get_conn)) -> StoredProfile:
    stored = await repo.get_profile(conn, business_id)
    if stored is None:
        raise HTTPException(404, "Business not found.")
    return stored


@app.put("/api/businesses/{business_id}/profile", response_model=StoredProfile)
async def confirm_profile(
    business_id: UUID, profile: BusinessProfile, conn: AsyncDatabase = Depends(get_conn)
) -> StoredProfile:
    """The owner confirms the (possibly edited) profile. Every submitted value becomes 'confirmed'."""
    if not profile.name.value.strip():
        raise HTTPException(422, "The business name can't be empty.")
    missing = [loc.label or loc.city or loc.address or "a location" for loc in profile.locations if not loc.country_code]
    if missing:
        raise HTTPException(422, f"Add a country for: {', '.join(missing)}.")
    if not any(loc.is_target for loc in profile.locations):
        raise HTTPException(422, "Add at least one place where you want customers to find you.")
    # Map positions let Google Maps grounding search from the business's own area (AI runs).
    profile = profile.model_copy(update={"locations": await fill_positions(profile.locations, get_geocoder())})
    stored = await repo.confirm_profile(conn, business_id, profile)
    if stored is None:
        raise HTTPException(404, "Business not found.")
    return stored


@app.post("/api/businesses/{business_id}/foundations", status_code=201, response_model=FoundationsOut)
async def create_foundations(business_id: UUID, conn: AsyncDatabase = Depends(get_conn)) -> FoundationsOut:
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
async def read_foundations(business_id: UUID, conn: AsyncDatabase = Depends(get_conn)) -> FoundationsOut:
    out = await repo.latest_foundations(conn, business_id)
    if out is None:
        raise HTTPException(404, "No foundation checks yet.")
    return FoundationsOut(**out)


# ---------------------------------------------------------------------------
# AI runs (build step 3)
# ---------------------------------------------------------------------------


async def _confirmed(conn: AsyncDatabase, business_id: UUID) -> StoredProfile:
    stored = await repo.get_profile(conn, business_id)
    if stored is None:
        raise HTTPException(404, "Business not found.")
    if not stored.confirmed:
        raise HTTPException(409, "Confirm your business profile first.")
    return stored


PAID_COMING_SOON = ["Screenshots of each answer", "Consumer-app checks (ChatGPT, Perplexity, Google AI Mode apps, "
                    "logged out, \"app view\")", "More platforms: Claude, Copilot, Google AI Mode",
                    "Report sent by email when complete"]


def _platform_options(defaults: set[str]) -> list[dict]:
    return [{"key": k, "label": PLATFORMS[k].label, "search_enabled": PLATFORMS[k].search_enabled,
             "default": k in defaults} for k in available_platforms()]


def _paid_platforms() -> list[str]:
    """Every search platform that's set up, plus Gemini without search for the search-off contrast."""
    ready = available_platforms()
    keys = [k for k in default_platforms()] + [k for k in ready if k == "chatgpt"]
    keys += [k for k in ready if not PLATFORMS[k].search_enabled]
    return list(dict.fromkeys(keys))


def _client_ip(request: Request) -> str | None:
    if os.getenv("AI_TRUST_FORWARDED_FOR") == "1":  # behind our own reverse proxy only
        fwd = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if fwd:
            return fwd
    return request.client.host if request.client else None


@app.get("/api/businesses/{business_id}/ai-prompts", response_model=PromptsOut)
async def read_ai_prompts(business_id: UUID, conn: AsyncDatabase = Depends(get_conn)) -> PromptsOut:
    """Suggested customer questions for the free run and the full audit, and the platforms that can answer them."""
    stored = await _confirmed(conn, business_id)
    defaults = set(default_platforms())
    p = stored.profile
    locs = airun.target_locations(p, all_locations=True)
    runs = airun.paid_runs()
    enabled = airun.paid_enabled()
    return PromptsOut(
        prompts=suggest_prompts(p), platforms=_platform_options(defaults), coming_soon=coming_soon(),
        full_prompts=full_audit_prompts(p),
        full_audit={
            "enabled": enabled,
            "message": None if enabled else "The full audit is coming soon. Payment isn't set up yet.",
            "max_core": PAID_CORE_MAX, "max_branded": PAID_BRANDED_MAX, "runs": runs, "branded_runs": 1,
            "platforms": _paid_platforms(), "search_off": any(not PLATFORMS[k].search_enabled
                                                              for k in _paid_platforms()),
            "locations": [loc["city"] for loc in locs if loc.get("city")],
            "budget": airun.budget_for("paid"), "coming_soon": PAID_COMING_SOON,
        },
        free_limits=airun.free_limits())


@app.post("/api/businesses/{business_id}/ai-runs", status_code=202)
async def create_ai_run(
    business_id: UUID, body: AIRunRequest, request: Request, conn: AsyncDatabase = Depends(get_conn),
    answerer: Answerer = Depends(get_answerer), reader: Reader = Depends(get_reader),
) -> dict:
    """Start a free run or a full audit in the background; poll GET /api/ai-runs/{audit_id} for results.

    Free run: a finished run of the same questions from the last hour is returned with reused=true instead of
    asking again; over the daily limits it's 429. Full audit: 403 until PAID_AUDITS_ENABLED=1.
    """
    stored = await _confirmed(conn, business_id)
    paid = body.tier == "paid"
    if paid and not airun.paid_enabled():
        raise HTTPException(403, "The full audit is coming soon: payment isn't set up yet. Try the free run.")
    prompts = [p for p in body.prompts if p.text.strip()]
    if not prompts:
        raise HTTPException(422, "Add at least one question.")
    if paid:
        branded = sum(1 for p in prompts if p.intent in BRANDED_INTENTS)
        if len(prompts) - branded > PAID_CORE_MAX:
            raise HTTPException(422, f"The full audit takes up to {PAID_CORE_MAX} customer questions.")
        if branded > PAID_BRANDED_MAX:
            raise HTTPException(422, f"The full audit takes up to {PAID_BRANDED_MAX} questions that use your name.")
    elif len(prompts) > FREE_RUN_MAX:
        raise HTTPException(422, f"The free run takes up to {FREE_RUN_MAX} questions.")
    platforms = list(dict.fromkeys(body.platforms or (_paid_platforms() if paid else default_platforms())))
    if paid and body.search_off:
        platforms += [k for k in available_platforms() if not PLATFORMS[k].search_enabled and k not in platforms]
    unknown = [p for p in platforms if p not in available_platforms()]
    if unknown:
        raise HTTPException(422, f"Not available: {', '.join(unknown)}.")
    if not platforms:
        raise HTTPException(503, "No AI platform is configured.")
    ip = _client_ip(request)
    if not paid:
        reuse = await airun.reusable_free_run(conn, business_id, prompts, platforms)
        if reuse is not None:
            return {"audit_id": reuse["_id"], "expected_runs": reuse["expected_runs"], "reused": True,
                    "tier": "free"}
        problem = await airun.free_limit_problem(conn, business_id, ip)
        if problem:
            raise HTTPException(429, problem)
    competitors = [c.value for c in stored.profile.suggested_competitors]
    try:
        audit = await airun.create_ai_audit(
            conn, business_id, stored.profile, prompts, platforms, runs=(body.runs or airun.paid_runs()) if paid else 1,
            tier=body.tier, requested_ip=ip, all_locations=paid and body.all_locations, branded_runs=1)
    except airun.AuditTooBig as exc:
        raise HTTPException(422, str(exc)) from None
    task = asyncio.create_task(airun.execute(conn, audit, stored.profile, competitors, answerer, reader))
    request.app.state.tasks.add(task)
    task.add_done_callback(request.app.state.tasks.discard)
    return {"audit_id": audit["_id"], "expected_runs": audit["expected_runs"], "reused": False, "tier": body.tier}


@app.get("/api/ai-runs/{audit_id}")
async def read_ai_run(audit_id: UUID, conn: AsyncDatabase = Depends(get_conn)) -> dict:
    audit = await airun.get_ai_audit(conn, str(audit_id))
    if audit is None:
        raise HTTPException(404, "AI run not found.")
    return airun.summarize(audit)


@app.get("/api/businesses/{business_id}/ai-runs/latest")
async def read_latest_ai_run(business_id: UUID, conn: AsyncDatabase = Depends(get_conn)) -> dict:
    audit = await airun.latest_ai_audit(conn, business_id)
    if audit is None:
        raise HTTPException(404, "No AI run yet.")
    return airun.summarize(audit)
