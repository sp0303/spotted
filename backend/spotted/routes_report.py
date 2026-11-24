"""Report and recommendations API (build steps 4 and 5): audit numbers and the action list.

  GET   /api/businesses/{business_id}/report                  the combined report (re-computed on each call;
                                                              numbers saved to audit_metrics, actions synced)
  GET   /api/businesses/{business_id}/actions                 the Action Center list
  PATCH /api/businesses/{business_id}/actions/{action_id}     {"status": "not_started|in_progress|done|dismissed"}
"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pymongo.asynchronous.database import AsyncDatabase

from . import repo
from .deps import get_conn
from .report import action_counts, build_report, list_actions, update_action_status

router = APIRouter(tags=["report"])


class ActionStatusIn(BaseModel):
    status: Literal["not_started", "in_progress", "done", "dismissed"]


@router.get("/api/businesses/{business_id}/report")
async def read_report(business_id: UUID, conn: AsyncDatabase = Depends(get_conn)) -> dict:
    out = await build_report(conn, business_id)
    if out is None:
        raise HTTPException(404, "Business not found.")
    return out


@router.get("/api/businesses/{business_id}/actions")
async def read_actions(business_id: UUID, conn: AsyncDatabase = Depends(get_conn)) -> dict:
    if await repo.get_profile(conn, business_id) is None:
        raise HTTPException(404, "Business not found.")
    actions = await list_actions(conn, str(business_id))
    return {"actions": actions, "action_counts": action_counts(actions)}


@router.patch("/api/businesses/{business_id}/actions/{action_id}")
async def patch_action(business_id: UUID, action_id: UUID, body: ActionStatusIn,
                       conn: AsyncDatabase = Depends(get_conn)) -> dict:
    out = await update_action_status(conn, str(business_id), str(action_id), body.status)
    if out is None:
        raise HTTPException(404, "Action not found.")
    return out
