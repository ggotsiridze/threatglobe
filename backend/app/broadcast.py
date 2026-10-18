"""Fan-out of pipeline messages to connected WebSocket clients.

Each client gets a bounded queue. A slow client drops its oldest messages
instead of blocking the pipeline or growing memory without bound.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any


class Broadcaster:
    def __init__(self, queue_size: int = 256) -> None:
        self._queues: set[asyncio.Queue] = set()
        self._queue_size = queue_size
        self.dropped = 0

    @property
    def client_count(self) -> int:
        return len(self._queues)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._queue_size)
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._queues.discard(queue)

    async def publish(self, message: dict[str, Any]) -> None:
        for queue in list(self._queues):
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
                    self.dropped += 1
            queue.put_nowait(message)
