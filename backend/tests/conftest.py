from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def make_settings(**overrides) -> Settings:
    base = {
        "DEMO_STREAM_ENABLED": False,
        "DEMO_HISTORY_HOURS": 1,
        "SNAPSHOT_INTERVAL_SECONDS": 0.2,
        "ELASTICSEARCH_URL": "https://es.internal.example:9200",
        "ELASTICSEARCH_PASSWORD": "super-secret-test-password",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(create_app(make_settings())) as c:
        yield c


@pytest.fixture(scope="module")
def private_client() -> Iterator[TestClient]:
    with TestClient(create_app(make_settings(PUBLIC_MODE=False))) as c:
        yield c


def cowrie_doc(**overrides) -> dict:
    doc = {
        "_id": "t-1",
        "@timestamp": "2026-01-15T10:00:00+00:00",
        "type": "Cowrie",
        "eventid": "cowrie.login.failed",
        "src_ip": "203.0.113.7",
        "src_port": 50123,
        "dest_ip": "192.0.2.10",
        "dest_port": 22,
        "protocol": "ssh",
        "username": "root",
        "password": "hunter2",
        "geoip": {
            "latitude": 39.9,
            "longitude": 116.4,
            "country_name": "China",
            "country_code2": "CN",
            "city_name": "Beijing",
            "asn": 64600,
            "as_org": "Example Cloud Hosting (CN)",
        },
    }
    doc.update(overrides)
    return doc
