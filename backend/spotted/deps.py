"""Shared FastAPI dependencies (imported by api.py and the feature routers, so routers don't import api.py)."""

from fastapi import Request
from pymongo.asynchronous.database import AsyncDatabase


async def get_conn(request: Request) -> AsyncDatabase:
    return request.app.state.db
