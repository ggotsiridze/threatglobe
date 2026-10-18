"""The single event pipeline: raw doc -> normalize -> risk -> store -> broadcast.

Demo data and (future) T-Pot data both enter through ``EventPipeline.ingest``.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime
from typing import Any

from .adapters.base import EventSource
from .broadcast import Broadcaster
from .models import AttackEvent
from .normalize import normalize_document
from .privacy import project_event
from .risk import RiskEngine
from .store import EventStore

log = logging.getLogger("threatglobe.pipeline")


class EventPipeline:
    def __init__(
        self,
        source: EventSource,
        store: EventStore,
        broadcaster: Broadcaster,
        *,
        public_mode: bool,
        stats_window_hours: int = 24,
        snapshot_interval: float = 5.0,
    ) -> None:
        self.source = source
        self.store = store
        self.broadcaster = broadcaster
        self.risk = RiskEngine()
        self.public_mode = public_mode
        self.stats_window_hours = stats_window_hours
        self.snapshot_interval = snapshot_interval
        self.started_at = datetime.now(UTC)
        self.ingested = 0
        self.rejected = 0
        self.last_event_at: datetime | None = None
        self._tasks: list[asyncio.Task] = []

    def ingest(self, raw: dict[str, Any]) -> AttackEvent | None:
        try:
            event = normalize_document(raw, raw_source_type=self.source.name)
        except Exception:  # normalization is defensive, but never kill the stream
            self.rejected += 1
            log.exception("failed to normalize document")
            return None
        self.risk.score(event)
        self.store.add(event)
        self.ingested += 1
        self.last_event_at = event.timestamp
        return event

    def project(self, event: AttackEvent) -> dict:
        return project_event(event, self.public_mode)

    def snapshot(self) -> dict:
        return {
            "stats": self.store.stats(self.stats_window_hours).model_dump(mode="json"),
            "timeline": self.store.timeline(self.stats_window_hours, 60).model_dump(mode="json"),
        }

    async def load_history(self) -> int:
        docs = await self.source.load_history()
        for doc in docs:
            self.ingest(doc)
        log.info("loaded %d historical events from %s", len(docs), self.source.name)
        return len(docs)

    async def _run_stream(self) -> None:
        async for raw in self.source.stream():
            event = self.ingest(raw)
            if event is not None:
                await self.broadcaster.publish({"type": "attack", "data": self.project(event)})

    async def _run_snapshots(self) -> None:
        while True:
            await asyncio.sleep(self.snapshot_interval)
            if self.broadcaster.client_count:
                await self.broadcaster.publish({"type": "snapshot", "data": self.snapshot()})

    def start(self, stream: bool = True) -> None:
        if stream:
            self._tasks.append(asyncio.create_task(self._run_stream(), name="event-stream"))
        self._tasks.append(asyncio.create_task(self._run_snapshots(), name="snapshots"))

    @property
    def streaming(self) -> bool:
        return any(t.get_name() == "event-stream" and not t.done() for t in self._tasks)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        self._tasks.clear()
        await self.source.close()
