"""T-Pot / Elasticsearch event source — REQUIRES REAL T-POT (not implemented).

Planned data path:  T-Pot -> Elasticsearch -> this adapter -> pipeline
(normalize -> risk -> store -> privacy) -> REST/WebSocket -> browser.

The browser never talks to Elasticsearch; credentials stay server-side.
Only the query construction is implemented now so the contract is testable.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from .base import EventSource


def build_search_query(after: datetime, size: int = 500) -> dict[str, Any]:
    """Elasticsearch query for documents newer than ``after``, oldest first."""
    return {
        "size": size,
        "sort": [{"@timestamp": {"order": "asc"}}],
        "query": {
            "bool": {
                "filter": [
                    {"range": {"@timestamp": {"gt": after.isoformat()}}},
                    {"exists": {"field": "src_ip"}},
                ]
            }
        },
    }


class TPotElasticsearchSource(EventSource):  # pragma: no cover - future work
    name = "tpot"
    mode = "live"

    def __init__(self, url: str, index: str, username: str | None = None, password: str | None = None):
        self.url = url
        self.index = index
        self._auth = (username, password) if username else None

    async def load_history(self) -> list[dict[str, Any]]:
        raise NotImplementedError("T-Pot integration is not implemented yet (REQUIRES REAL T-POT)")

    async def stream(self) -> AsyncIterator[dict[str, Any]]:
        raise NotImplementedError("T-Pot integration is not implemented yet (REQUIRES REAL T-POT)")
        yield {}
