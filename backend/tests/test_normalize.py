from datetime import UTC, datetime

import pytest

from app.models import EventType
from app.normalize import normalize_document, service_for_port
from tests.conftest import cowrie_doc


def test_full_cowrie_document_maps_every_field():
    e = normalize_document(cowrie_doc(), raw_source_type="demo")
    assert e.timestamp == datetime(2026, 1, 15, 10, tzinfo=UTC)
    assert e.source_ip == "203.0.113.7"
    assert (e.source_latitude, e.source_longitude) == (39.9, 116.4)
    assert e.source_country == "China" and e.source_country_code == "CN"
    assert e.source_city == "Beijing"
    assert e.source_asn == 64600
    assert e.source_organization == "Example Cloud Hosting (CN)"
    assert e.destination_ip == "192.0.2.10"
    assert e.destination_port == 22
    assert e.protocol == "ssh"
    assert e.honeypot == "Cowrie"
    assert e.username == "root" and e.password == "hunter2"
    assert e.event_type is EventType.LOGIN_ATTEMPT
    assert e.raw_source_type == "demo"


@pytest.mark.parametrize("doc", [{}, None, [], "garbage", 42, {"_source": {}}])
def test_empty_or_invalid_documents_do_not_crash(doc):
    e = normalize_document(doc)
    assert e.id and e.timestamp.tzinfo is not None
    assert e.honeypot == "unknown"
    assert e.source_ip is None and e.source_latitude is None


def test_bad_field_values_become_none():
    e = normalize_document(
        cowrie_doc(
            src_ip="999.1.1.1",
            dest_port="not-a-port",
            geoip={"latitude": "abc", "longitude": 500, "asn": "AS-bogus"},
            username="  ",
            **{"@timestamp": "yesterday"},
        )
    )
    assert e.source_ip is None
    assert e.destination_port is None
    assert e.source_latitude is None and e.source_longitude is None
    assert e.source_asn is None
    assert e.username is None
    assert e.timestamp.tzinfo is not None  # falls back to now


def test_elasticsearch_hit_wrapper_and_epoch_timestamp():
    hit = {"_id": "abc", "_source": cowrie_doc(**{"@timestamp": 1768471200000})}
    e = normalize_document(hit)
    assert e.timestamp == datetime(2026, 1, 15, 10, tzinfo=UTC)
    assert e.source_ip == "203.0.113.7"


def test_ids_are_stable_and_do_not_contain_ip():
    a = normalize_document(cowrie_doc())
    b = normalize_document(cowrie_doc())
    assert a.id == b.id
    assert "203.0.113.7" not in a.id


def test_control_characters_are_stripped_and_text_truncated():
    e = normalize_document(cowrie_doc(username="ro\x00ot\x1b[31m", input="A" * 5000))
    assert e.username == "root[31m"
    assert len(e.command) == 256


@pytest.mark.parametrize(
    ("eventid", "expected"),
    [
        ("cowrie.session.connect", EventType.CONNECTION),
        ("cowrie.login.success", EventType.LOGIN_SUCCESS),
        ("cowrie.command.input", EventType.COMMAND),
        ("cowrie.session.file_download", EventType.MALWARE),
        ("dionaea.download.complete", EventType.MALWARE),
        ("honeytrap.connection", EventType.SCAN),
        ("suricata.alert", EventType.EXPLOIT),
    ],
)
def test_event_id_mapping(eventid, expected):
    assert normalize_document(cowrie_doc(eventid=eventid)).event_type is expected


def test_protocol_inferred_from_port_when_missing():
    doc = cowrie_doc(dest_port=3389)
    doc.pop("protocol")
    assert normalize_document(doc).protocol == "rdp"
    assert service_for_port(None) is None
