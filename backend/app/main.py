"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .adapters.base import EventSource
from .adapters.demo import DemoEventSource
from .api import routes, ws
from .broadcast import Broadcaster
from .config import Settings, get_settings
from .pipeline import EventPipeline
from .store import EventStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def build_source(settings: Settings) -> EventSource:
    if settings.source == "demo":
        return DemoEventSource(
            settings.demo_data_path,
            settings.demo_events_per_second,
            history_hours=settings.demo_history_hours,
            max_history_events=settings.max_stored_events,
        )
    raise RuntimeError(
        "THREATGLOBE_SOURCE=tpot is not available yet: the T-Pot/Elasticsearch adapter "
        "REQUIRES REAL T-POT and has not been implemented. Use THREATGLOBE_SOURCE=demo."
    )


def create_app(settings: Settings | None = None, source: EventSource | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        pipeline = EventPipeline(
            source or build_source(settings),
            EventStore(settings.max_stored_events),
            Broadcaster(),
            public_mode=settings.public_mode,
            stats_window_hours=settings.stats_window_hours,
            timeline_hours=settings.timeline_hours,
            timeline_bucket_minutes=settings.timeline_bucket_minutes,
            snapshot_interval=settings.snapshot_interval_seconds,
        )
        app.state.pipeline = pipeline
        await pipeline.load_history()
        pipeline.start(stream=settings.demo_stream_enabled)
        try:
            yield
        finally:
            await pipeline.stop()

    app = FastAPI(
        title="ThreatGlobe API",
        version=__version__,
        description="Honeypot telemetry visualization API (defensive use only).",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(routes.router)
    app.include_router(ws.router)
    return app


app = create_app()
