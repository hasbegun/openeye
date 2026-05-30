"""Alerts REST endpoints."""

from typing import Optional

import asyncpg
from fastapi import APIRouter, Query, HTTPException

from shared.config import ServiceConfig
from shared.schemas import AlertMessage

router = APIRouter(prefix="/alerts", tags=["alerts"])

config = ServiceConfig()
_pool = None


async def get_pool() -> asyncpg.Pool:
    """Lazy-init database pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            config.database.dsn,
            min_size=1,
            max_size=5,
        )
    return _pool


@router.get("", response_model=list[AlertMessage])
async def list_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    min_severity: Optional[int] = Query(default=None, ge=0, le=10),
    source_id: Optional[str] = Query(default=None),
):
    """Retrieve alerts from database, ordered by most recent."""
    pool = await get_pool()

    query = "SELECT id, frame_id, source_id, description, severity, tags, thumbnail_base64, created_at FROM alerts"
    conditions = []
    params = []
    idx = 1

    if min_severity is not None:
        conditions.append(f"severity >= ${idx}")
        params.append(min_severity)
        idx += 1

    if source_id is not None:
        conditions.append(f"source_id = ${idx}")
        params.append(source_id)
        idx += 1

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += f" ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
    params.extend([limit, offset])

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return [
        AlertMessage(
            alert_id=str(row["id"]),
            frame_id=row["frame_id"],
            source_id=row["source_id"],
            description=row["description"],
            severity=row["severity"],
            tags=row["tags"] or [],
            thumbnail_base64=row["thumbnail_base64"],
            timestamp=row["created_at"],
        )
        for row in rows
    ]


@router.get("/count")
async def alert_count(
    min_severity: Optional[int] = Query(default=None, ge=0, le=10),
):
    """Get total alert count."""
    pool = await get_pool()

    query = "SELECT COUNT(*) FROM alerts"
    params = []

    if min_severity is not None:
        query += " WHERE severity >= $1"
        params.append(min_severity)

    async with pool.acquire() as conn:
        count = await conn.fetchval(query, *params)

    return {"count": count}
