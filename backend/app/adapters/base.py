"""Event source contract.

An ``EventSource`` produces *raw* documents in T-Pot/Elasticsearch shape. It
never normalizes or scores; that is the pipeline's job, so every source flows
through identical normalization, risk scoring, storage and privacy code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Literal


class EventSource(ABC):
    #: Short identifier stored on each event as ``raw_source_type``.
    name: str
    #: "demo" for sanitized sample data, "live" for real sensor telemetry.
    mode: Literal["demo", "live"]

    @abstractmethod
    async def load_history(self) -> list[dict[str, Any]]:
        """Return historical documents, oldest first."""

    @abstractmethod
    def stream(self) -> AsyncIterator[dict[str, Any]]:
        """Yield new documents as they arrive, in chronological order."""

    async def close(self) -> None:  # pragma: no cover - optional hook
        return None
