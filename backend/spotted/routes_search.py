"""Search and listings API (build step 6): search results, Maps/local pack, business listings.

Owned by the search workstream. Logic lives in search.py.

  POST /api/businesses/{id}/search   start a check (202); runs in the background, results saved as they arrive
  (also Google News RSS for press mentions: the client, category roundups and top competitors)
  GET  /api/businesses/{id}/search   latest check: status, summary (the shape the report reads) and per-query details
"""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pymongo.asynchronous.database import AsyncDatabase

from . import repo, search
from .config import settings
from .deps import get_conn
from .platforms import Answerer, LiveAnswerer

router = APIRouter(tags=["search"])

_answerer: Answerer | None = None


def get_search_answerer() -> Answerer:
    """Gemini with Search or Maps grounding (one tool per call). Overridden in tests."""
    global _answerer
    if not settings.gemini_api_key:
        raise HTTPException(503, "GEMINI_API_KEY is not set.")
    if _answerer is None:
        _answerer = LiveAnswerer()
    return _answerer


def get_news_fetcher() -> search.NewsFetcher:
    """Google News RSS (free, no key); a fresh one per run so its cache lasts one run. Overridden in tests."""
    return search.GoogleNewsRSS()


@router.post("/api/businesses/{business_id}/search", status_code=202)
async def start_search(business_id: UUID, request: Request, conn: AsyncDatabase = Depends(get_conn),
                       answerer: Answerer = Depends(get_search_answerer),
                       news: search.NewsFetcher = Depends(get_news_fetcher)) -> dict:
    """Check search engines, Google Maps and listings for the confirmed profile, in the background."""
    stored = await repo.get_profile(conn, business_id)
    if stored is None:
        raise HTTPException(404, "Business not found.")
    if not stored.confirmed:
        raise HTTPException(409, "Confirm your business profile first.")
    running = await search.latest_search_audit(conn, business_id)
    if running and running["status"] == "running":  # don't pay twice for the same check
        return {"audit_id": running["_id"], "expected_calls": running["expected_calls"]}
    audit = await search.create_search_audit(conn, business_id, stored.profile)
    task = asyncio.create_task(search.execute(conn, audit, answerer, news))
    tasks = getattr(request.app.state, "tasks", None)
    if tasks is not None:  # keep a reference so the task isn't garbage-collected
        tasks.add(task)
        task.add_done_callback(tasks.discard)
    return {"audit_id": audit["_id"], "expected_calls": audit["expected_calls"]}


@router.get("/api/businesses/{business_id}/search")
async def read_search(business_id: UUID, conn: AsyncDatabase = Depends(get_conn)) -> dict:
    audit = await search.latest_search_audit(conn, business_id)
    if audit is None:
        raise HTTPException(404, "No search check yet.")
    return search.details(audit)
