"""REST endpoints. Every event leaves the server through ``pipeline.project``."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request

from .. import __version__
from ..models import Severity
from ..pipeline import EventPipeline
from ..risk import describe_rules

router = APIRouter()

Hours = Annotated[int, Query(ge=1, le=168)]


def _pipeline(request: Request) -> EventPipeline:
    return request.app.state.pipeline


@router.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}


@router.get("/api/status", tags=["meta"])
async def status(request: Request) -> dict:
    p = _pipeline(request)
    settings = request.app.state.settings
    now = datetime.now(UTC)
    return {
        "app": settings.app_name,
        "version": __version__,
        "mode": p.source.mode,
        "source": p.source.name,
        "public_mode": p.public_mode,
        "streaming": p.streaming,
        "connected_clients": p.broadcaster.client_count,
        "events_stored": len(p.store),
        "events_ingested": p.ingested,
        "events_rejected": p.rejected,
        "last_event_at": p.last_event_at,
        "uptime_seconds": int((now - p.started_at).total_seconds()),
        "server_time": now,
        "sensor": {
            "name": settings.sensor_name,
            "city": settings.sensor_city,
            "country": settings.sensor_country,
            "latitude": settings.sensor_latitude,
            "longitude": settings.sensor_longitude,
        },
        "risk_rules": describe_rules(),
    }


@router.get("/api/stats", tags=["analytics"])
async def stats(request: Request, hours: Hours = 24) -> dict:
    return _pipeline(request).store.stats(hours).model_dump(mode="json")


@router.get("/api/events", tags=["events"])
async def events(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=5000)] = 100,
    since: datetime | None = None,
    until: datetime | None = None,
    severity: Severity | None = None,
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    honeypot: Annotated[str | None, Query(max_length=64)] = None,
    port: Annotated[int | None, Query(ge=0, le=65535)] = None,
    order: Literal["asc", "desc"] = "desc",
) -> dict:
    p = _pipeline(request)
    if since and since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until and until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    found = p.store.query(
        limit=limit, since=since, until=until, severity=severity,
        country=country, honeypot=honeypot, port=port, order=order,
    )  # fmt: skip
    return {"count": len(found), "events": [p.project(e) for e in found]}


@router.get("/api/events/{event_id}", tags=["events"])
async def event_detail(request: Request, event_id: str) -> dict:
    p = _pipeline(request)
    event = p.store.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    return p.project(event)


@router.get("/api/countries", tags=["analytics"])
async def countries(request: Request, hours: Hours = 24, limit: Annotated[int, Query(ge=1, le=250)] = 20) -> dict:
    return {"items": [c.model_dump() for c in _pipeline(request).store.countries(hours, limit)]}


@router.get("/api/ports", tags=["analytics"])
async def ports(request: Request, hours: Hours = 24, limit: Annotated[int, Query(ge=1, le=100)] = 20) -> dict:
    return {"items": [c.model_dump() for c in _pipeline(request).store.ports(hours, limit)]}


@router.get("/api/honeypots", tags=["analytics"])
async def honeypots(request: Request, hours: Hours = 24, limit: Annotated[int, Query(ge=1, le=100)] = 20) -> dict:
    return {"items": [c.model_dump() for c in _pipeline(request).store.honeypots(hours, limit)]}


@router.get("/api/timeline", tags=["analytics"])
async def timeline(
    request: Request,
    hours: Hours = 24,
    bucket_minutes: Annotated[int, Query(ge=1, le=1440)] = 60,
) -> dict:
    return _pipeline(request).store.timeline(hours, bucket_minutes).model_dump(mode="json")
