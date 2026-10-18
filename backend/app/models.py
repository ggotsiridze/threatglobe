"""Normalized data model shared by every event source (demo today, T-Pot later).

Every adapter must turn its raw records into ``AttackEvent`` objects. Everything
downstream (risk scoring, storage, privacy, REST, WebSocket, UI) only ever sees
this model, which is what lets demo telemetry and real honeypot telemetry use
the exact same pipeline.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EventType(StrEnum):
    CONNECTION = "connection"
    SCAN = "scan"
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    COMMAND = "command"
    MALWARE = "malware"
    EXPLOIT = "exploit"
    WEB_REQUEST = "web_request"
    OTHER = "other"


class RiskFactor(BaseModel):
    """One transparent, human-readable rule that contributed to a risk score."""

    rule: str
    points: int
    detail: str


class AttackEvent(BaseModel):
    """A single normalized honeypot observation.

    Only ``id`` and ``timestamp`` are guaranteed; every other field may be
    missing in raw telemetry and must be treated as optional by consumers.
    """

    model_config = ConfigDict(use_enum_values=False)

    id: str
    timestamp: datetime

    source_ip: str | None = None
    source_latitude: float | None = None
    source_longitude: float | None = None
    source_country: str | None = None
    source_country_code: str | None = None
    source_city: str | None = None
    source_asn: int | None = None
    source_organization: str | None = None

    destination_ip: str | None = None
    destination_port: int | None = None
    protocol: str | None = None
    honeypot: str = "unknown"

    username: str | None = None
    password: str | None = None
    command: str | None = None

    event_type: EventType = EventType.OTHER
    severity: Severity = Severity.LOW
    risk_score: int = 0
    risk_factors: list[RiskFactor] = Field(default_factory=list)

    raw_source_type: str = "unknown"
    raw: dict[str, Any] | None = None

    @property
    def has_geo(self) -> bool:
        return self.source_latitude is not None and self.source_longitude is not None


class CountStat(BaseModel):
    key: str
    label: str
    count: int


class StatsSnapshot(BaseModel):
    events_today: int
    unique_source_ips: int
    countries_observed: int
    most_targeted_service: str | None
    events_last_minute: int
    severity_counts: dict[str, int]
    top_countries: list[CountStat]
    top_ports: list[CountStat]
    top_honeypots: list[CountStat]
    window_hours: int
    generated_at: datetime


class TimelineBucket(BaseModel):
    start: datetime
    total: int
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0


class Timeline(BaseModel):
    bucket_minutes: int
    buckets: list[TimelineBucket]
