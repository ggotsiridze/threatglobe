"""Event source adapters. Each yields raw T-Pot-shaped documents."""

from .base import EventSource
from .demo import DemoEventSource

__all__ = ["EventSource", "DemoEventSource"]
