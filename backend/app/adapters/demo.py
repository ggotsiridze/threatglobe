"""Demo event source backed by a sanitized JSON dataset.

The dataset (``backend/data/demo_events.json``) is synthetic: it uses RFC 5737
documentation IP ranges, private-use ASNs and fictional organization names.
Its documents use the same T-Pot field layout as real Elasticsearch hits.

Timing: the dataset's own recorded inter-arrival gaps (bursty brute-force
sessions, quiet periods) are kept, but uniformly scaled so the average rate
equals ``events_per_second``. The dataset is played as an endless loop:

* ``load_history`` lays the loop *backwards* from "now" to cover the last
  ``history_hours``, so the dashboard opens with history at the same density
  as the live stream (no artificial cliff in the volume chart).
* ``stream`` continues the loop forward in real time, stamping each document
  with the current time and a fresh id.
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

MAX_GAP_SECONDS = 2.5


class DemoEventSource(EventSource):
    name = "demo"
    mode = "demo"

    def __init__(
        self,
        path: Path,
        events_per_second: float = 1.2,
        history_hours: float = 6.0,
        max_history_events: int = 50_000,
        rng: random.Random | None = None,
        clock=None,
    ) -> None:
        self.path = Path(path)
        self.events_per_second = max(0.05, events_per_second)
        self.history_hours = max(0.0, history_hours)
        self.max_history_events = max(0, max_history_events)
        self._rng = rng or random.Random()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._docs: list[dict[str, Any]] | None = None
        self._gaps: list[float] = []

    def _load(self) -> list[dict[str, Any]]:
        if self._docs is None:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            docs = payload.get("events", []) if isinstance(payload, dict) else payload
            docs = [d for d in docs if isinstance(d, dict)]
            docs.sort(key=lambda d: parse_timestamp(d.get("@timestamp")))
            self._docs = docs
            self._gaps = self._scaled_gaps(docs)
        return self._docs

    def _scaled_gaps(self, docs: list[dict[str, Any]]) -> list[float]:
        """``gaps[i]`` = seconds between doc ``i-1`` and doc ``i`` (wrapping)."""
        if not docs:
            return []
        times = [parse_timestamp(d.get("@timestamp")).timestamp() for d in docs]
        raw = [max(0.0, times[i] - times[i - 1]) for i in range(1, len(times))]
        mean = (sum(raw) / len(raw)) if raw and sum(raw) > 0 else 1.0
        raw.insert(0, mean)  # wrap-around gap from the last doc back to the first
        # Scale so the mean gap is 1/rate; re-solve a few times because capping
        # long quiet gaps would otherwise push the effective rate above target.
        target = 1.0 / self.events_per_second
        scale = target / mean
        for _ in range(8):
            gaps = [min(MAX_GAP_SECONDS, g * scale) for g in raw]
            achieved = sum(gaps) / len(gaps)
            if achieved <= 0 or abs(achieved - target) / target < 0.01:
                break
            scale *= target / achieved
        return gaps

    @property
    def size(self) -> int:
        return len(self._load())

    async def load_history(self) -> list[dict[str, Any]]:
        docs = self._load()
        if not docs or self.history_hours == 0:
            return []
        now = self._clock()
        start = now - timedelta(hours=self.history_hours)
        t = now - timedelta(seconds=1)
        out: list[dict[str, Any]] = []
        i, lap = len(docs) - 1, 0
        while t > start and len(out) < self.max_history_events:
            copy = dict(docs[i])
            copy["@timestamp"] = t.isoformat()
            copy["_id"] = f"{docs[i].get('_id', 'demo')}-h{lap}"
            out.append(copy)
            t -= timedelta(seconds=self._gaps[i])
            i -= 1
            if i < 0:
                i, lap = len(docs) - 1, lap + 1
        out.reverse()
        return out

    async def stream(self) -> AsyncIterator[dict[str, Any]]:
        docs = self._load()
        if not docs:
            return
        cycle = 0
        while True:
            cycle += 1
            for i, doc in enumerate(docs):
                jitter = self._rng.uniform(0.85, 1.15)
                await asyncio.sleep(self._gaps[i] * jitter)
                copy = dict(doc)
                copy["@timestamp"] = self._clock().isoformat()
                copy["_id"] = f"{doc.get('_id', 'demo')}-c{cycle}"
                yield copy
