"""Runtime configuration, read from environment variables.

Secrets (e.g. a future Elasticsearch password) live here and are never
serialized into API responses; ``public_status`` exposes only safe fields.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DEMO_PATH = Path(__file__).resolve().parent.parent / "data" / "demo_events.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ThreatGlobe"
    source: Literal["demo", "tpot"] = Field(default="demo", alias="THREATGLOBE_SOURCE")
    public_mode: bool = Field(default=True, alias="PUBLIC_MODE")
    cors_origins: str = Field(default="http://localhost:5173,http://localhost:8080", alias="CORS_ORIGINS")

    # Demo source
    demo_data_path: Path = Field(default=DEFAULT_DEMO_PATH, alias="DEMO_DATA_PATH")
    demo_events_per_second: float = Field(default=1.2, alias="DEMO_EVENTS_PER_SECOND")
    demo_history_hours: float = Field(default=6.0, alias="DEMO_HISTORY_HOURS")
    demo_stream_enabled: bool = Field(default=True, alias="DEMO_STREAM_ENABLED")

    # Sensor (honeypot destination) shown on the globe. Deliberately coarse.
    sensor_name: str = Field(default="tpot-demo-01", alias="SENSOR_NAME")
    sensor_city: str = Field(default="Frankfurt", alias="SENSOR_CITY")
    sensor_country: str = Field(default="Germany", alias="SENSOR_COUNTRY")
    sensor_latitude: float = Field(default=50.11, alias="SENSOR_LATITUDE")
    sensor_longitude: float = Field(default=8.68, alias="SENSOR_LONGITUDE")

    # Store / streaming
    max_stored_events: int = Field(default=50_000, alias="MAX_STORED_EVENTS")
    stats_window_hours: int = Field(default=24, alias="STATS_WINDOW_HOURS")
    timeline_hours: int = Field(default=6, alias="TIMELINE_HOURS")
    timeline_bucket_minutes: int = Field(default=10, alias="TIMELINE_BUCKET_MINUTES")
    snapshot_interval_seconds: float = Field(default=5.0, alias="SNAPSHOT_INTERVAL_SECONDS")

    # Future T-Pot / Elasticsearch source (REQUIRES REAL T-POT). Never exposed.
    elasticsearch_url: str | None = Field(default=None, alias="ELASTICSEARCH_URL")
    elasticsearch_username: str | None = Field(default=None, alias="ELASTICSEARCH_USERNAME")
    elasticsearch_password: SecretStr | None = Field(default=None, alias="ELASTICSEARCH_PASSWORD")
    elasticsearch_index: str = Field(default="logstash-*", alias="ELASTICSEARCH_INDEX")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
