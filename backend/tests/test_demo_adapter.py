import asyncio
import ipaddress
import json
import random
from datetime import UTC, datetime

from app.adapters.demo import DemoEventSource
from app.adapters.tpot import build_search_query
from app.config import DEFAULT_DEMO_PATH
from app.normalize import normalize_document, parse_timestamp

DOC_NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]


def load_raw():
    return json.loads(DEFAULT_DEMO_PATH.read_text())


def test_dataset_is_sanitized():
    payload = load_raw()
    assert "Not real attacks" in payload["meta"]["description"]
    for doc in payload["events"]:
        assert any(ipaddress.ip_address(doc["src_ip"]) in n for n in DOC_NETS), doc["src_ip"]
        asn = doc.get("geoip", {}).get("asn")
        assert asn is None or 64512 <= asn <= 65534
    assert len(payload["events"]) >= 1000


def test_every_demo_document_normalizes():
    for doc in load_raw()["events"]:
        normalize_document(doc, raw_source_type="demo")


def test_history_is_rebased_to_now_and_chronological():
    fixed_now = datetime(2026, 10, 1, 12, tzinfo=UTC)
    src = DemoEventSource(DEFAULT_DEMO_PATH, clock=lambda: fixed_now)
    history = asyncio.run(src.load_history())
    times = [parse_timestamp(d["@timestamp"]) for d in history]
    assert times == sorted(times)
    assert (fixed_now - times[-1]).total_seconds() == 5
    assert (times[-1] - times[0]).total_seconds() < 24 * 3600
    assert len({d["_id"] for d in history}) == len(history)


def test_stream_yields_fresh_ids_in_order():
    async def take(n):
        src = DemoEventSource(DEFAULT_DEMO_PATH, events_per_second=10_000, rng=random.Random(1))
        out = []
        async for doc in src.stream():
            out.append(doc)
            if len(out) == n:
                break
        return out

    docs = asyncio.run(take(50))
    stamps = [d["@timestamp"] for d in docs]
    assert stamps == sorted(stamps)
    assert len({d["_id"] for d in docs}) == 50


def test_empty_dataset(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text('{"events": []}')
    assert asyncio.run(DemoEventSource(path).load_history()) == []


def test_tpot_query_contract():
    q = build_search_query(datetime(2026, 1, 1, tzinfo=UTC), size=10)
    assert q["size"] == 10 and q["sort"][0]["@timestamp"]["order"] == "asc"
