"""WebSocket stream of new attacks: /ws/attacks.

Protocol (server -> client JSON messages):

* ``{"type": "hello", "data": {mode, public_mode, sensor, recent: [...], snapshot}}``
  sent once on connect so the client can render without extra REST calls.
* ``{"type": "attack", "data": AttackEvent}`` for every new event.
* ``{"type": "snapshot", "data": {stats, timeline}}`` every few seconds.
* ``{"type": "pong"}`` in reply to a client ``"ping"`` text frame.
"""

from __future__ import annotations

import asyncio
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..pipeline import EventPipeline

router = APIRouter()


@router.websocket("/ws/attacks")
async def attacks(websocket: WebSocket) -> None:
    pipeline: EventPipeline = websocket.app.state.pipeline
    settings = websocket.app.state.settings
    await websocket.accept()
    queue = pipeline.broadcaster.subscribe()
    try:
        recent = pipeline.store.query(limit=40, order="desc")
        await websocket.send_json(
            {
                "type": "hello",
                "data": {
                    "mode": pipeline.source.mode,
                    "public_mode": pipeline.public_mode,
                    "sensor": {
                        "name": settings.sensor_name,
                        "latitude": settings.sensor_latitude,
                        "longitude": settings.sensor_longitude,
                        "city": settings.sensor_city,
                        "country": settings.sensor_country,
                    },
                    "recent": [pipeline.project(e) for e in reversed(recent)],
                    "snapshot": pipeline.snapshot(),
                },
            }
        )

        async def sender() -> None:
            while True:
                await websocket.send_json(await queue.get())

        async def receiver() -> None:
            while True:
                message = await websocket.receive_text()
                if message == "ping" and not queue.full():
                    queue.put_nowait({"type": "pong"})

        tasks = [asyncio.create_task(sender()), asyncio.create_task(receiver())]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for task in pending:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, WebSocketDisconnect):
                raise exc
    except WebSocketDisconnect:
        pass
    finally:
        pipeline.broadcaster.unsubscribe(queue)
