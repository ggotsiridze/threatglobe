"""Demo event source backed by a sanitized JSON dataset.

The dataset (``backend/data/demo_events.json``) is synthetic: it uses RFC 5737
documentation IP ranges, private-use ASNs and fictional organization names.
Its documents use the same T-Pot field layout as real Elasticsearch hits.

* ``load_history`` rebases the recorded timeline so it ends "now", giving the
  dashboard a realistic last-24h history.
* ``stream`` then replays the dataset in chronological order forever, stamping
  each document with the current time and a fresh id, at a configurable rate.
"""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ..normalize import parse_timestamp
from .base import EventSource


class DemoEventSource(EventSource):
    name = "demo"
    mode = "demo"

    def __init__(
        self,
        path: Path,
        events_per_second: float = 1.5,
        rng: random.Random | None = None,
        clock=None,
    ) -> None:
        self.path = Path(path)
        self.events_per_second = max(0.05, events_per_second)
        self._rng = rng or random.Random()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._docs: list[dict[str, Any]] | None = None

    def _load(self) -> list[dict[str, Any]]:
        if self._docs is None:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            docs = payload.get("events", []) if isinstance(payload, dict) else payload
            docs = [d for d in docs if isinstance(d, dict)]
            docs.sort(key=lambda d: parse_timestamp(d.get("@timestamp")))
            self._docs = docs
        return self._docs

    @property
    def size(self) -> int:
        return len(self._load())

    async def load_history(self) -> list[dict[str, Any]]:
        docs = self._load()
        if not docs:
            return []
        last = parse_timestamp(docs[-1].get("@timestamp"))
        shift = (self._clock() - timedelta(seconds=5)) - last
        rebased = []
        for doc in docs:
            copy = dict(doc)
            copy["@timestamp"] = (parse_timestamp(doc.get("@timestamp")) + shift).isoformat()
            copy["_id"] = f"{doc.get('_id', 'demo')}-h"
            rebased.append(copy)
        return rebased

    async def stream(self) -> AsyncIterator[dict[str, Any]]:
        docs = self._load()
        if not docs:
            return
        cycle = 0
        while True:
            cycle += 1
            for doc in docs:
                await asyncio.sleep(self._rng.expovariate(self.events_per_second))
                copy = dict(doc)
                copy["@timestamp"] = self._clock().isoformat()
                copy["_id"] = f"{doc.get('_id', 'demo')}-c{cycle}"
                yield copy
