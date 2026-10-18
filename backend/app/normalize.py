"""Normalize raw honeypot documents into ``AttackEvent``.

The input shape is the T-Pot / Logstash Elasticsearch document format
(``@timestamp``, ``src_ip``, ``dest_port``, ``type``, ``eventid``, ``geoip.*``
...). Demo telemetry is stored in this same shape on purpose, so the demo
adapter and the future Elasticsearch adapter both call ``normalize_document``.

The function is deliberately forgiving: any field can be missing, have the
wrong type, or be garbage, and the result is still a valid ``AttackEvent``.
"""

from __future__ import annotations

import hashlib
import ipaddress
from datetime import UTC, datetime
from typing import Any

from .models import AttackEvent, EventType

# Well-known ports -> service label. Used for "most targeted service".
PORT_SERVICES: dict[int, str] = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    102: "S7comm",
    110: "POP3",
    135: "MSRPC",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    502: "Modbus",
    1433: "MSSQL",
    1883: "MQTT",
    2222: "SSH",
    2223: "Telnet",
    3306: "MySQL",
    3389: "RDP",
    5060: "SIP",
    5432: "PostgreSQL",
    5900: "VNC",
    6379: "Redis",
    8080: "HTTP-Alt",
    8443: "HTTPS-Alt",
    9200: "Elasticsearch",
    11211: "Memcached",
    27017: "MongoDB",
}

# Cowrie / Dionaea / generic event ids -> normalized event type.
EVENT_ID_MAP: dict[str, EventType] = {
    "cowrie.session.connect": EventType.CONNECTION,
    "cowrie.client.version": EventType.CONNECTION,
    "cowrie.login.failed": EventType.LOGIN_ATTEMPT,
    "cowrie.login.success": EventType.LOGIN_SUCCESS,
    "cowrie.command.input": EventType.COMMAND,
    "cowrie.command.failed": EventType.COMMAND,
    "cowrie.session.file_download": EventType.MALWARE,
    "cowrie.session.file_upload": EventType.MALWARE,
    "dionaea.connection": EventType.CONNECTION,
    "dionaea.download.complete": EventType.MALWARE,
    "dionaea.login": EventType.LOGIN_ATTEMPT,
    "heralding.auth": EventType.LOGIN_ATTEMPT,
    "honeytrap.connection": EventType.SCAN,
    "conpot.request": EventType.EXPLOIT,
    "tanner.request": EventType.WEB_REQUEST,
    "suricata.alert": EventType.EXPLOIT,
    "mailoney.connection": EventType.CONNECTION,
}

MAX_TEXT = 256


def service_for_port(port: int | None) -> str | None:
    if port is None:
        return None
    return PORT_SERVICES.get(port)


def _get(doc: dict[str, Any], *paths: str) -> Any:
    """Return the first non-empty value among dotted ``paths``."""
    for path in paths:
        node: Any = doc
        for part in path.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                node = None
                break
        if node not in (None, "", [], {}):
            return node
    return None


def _text(value: Any, limit: int = MAX_TEXT) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    # Strip control characters; telemetry is attacker-controlled input.
    cleaned = "".join(ch for ch in value if ch.isprintable())
    cleaned = cleaned.strip()
    if not cleaned:
        return None
    return cleaned[:limit]


def _int(value: Any, lo: int | None = None, hi: int | None = None) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip().upper().removeprefix("AS")
    try:
        result = int(float(value))
    except (TypeError, ValueError):
        return None
    if lo is not None and result < lo:
        return None
    if hi is not None and result > hi:
        return None
    return result


def _float(value: Any, lo: float, hi: float) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result or not lo <= result <= hi:  # NaN or out of range
        return None
    return result


def _ip(value: Any) -> str | None:
    text = _text(value, 64)
    if text is None:
        return None
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        return None


def parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        ts = value
    elif isinstance(value, int | float) and not isinstance(value, bool):
        # epoch seconds or milliseconds
        seconds = value / 1000 if value > 1e11 else value
        try:
            ts = datetime.fromtimestamp(seconds, tz=UTC)
        except (OverflowError, OSError, ValueError):
            ts = datetime.now(UTC)
    elif isinstance(value, str):
        try:
            ts = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            ts = datetime.now(UTC)
    else:
        ts = datetime.now(UTC)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _event_type(doc: dict[str, Any], honeypot: str) -> EventType:
    explicit = _text(_get(doc, "event_type"), 64)
    if explicit:
        try:
            return EventType(explicit.lower())
        except ValueError:
            pass
    event_id = _text(_get(doc, "eventid"), 64)
    if event_id:
        mapped = EVENT_ID_MAP.get(event_id.lower())
        if mapped:
            return mapped
    if _get(doc, "alert.signature"):
        return EventType.EXPLOIT
    hp = honeypot.lower()
    if hp in ("honeytrap", "ddospot", "fatt", "p0f"):
        return EventType.SCAN
    if hp in ("tanner", "snare", "wordpot", "h0neytr4p"):
        return EventType.WEB_REQUEST
    if _get(doc, "username"):
        return EventType.LOGIN_ATTEMPT
    if _get(doc, "src_ip"):
        return EventType.CONNECTION
    return EventType.OTHER


def _stable_id(doc: dict[str, Any]) -> str:
    raw_id = _text(_get(doc, "_id", "id", "event_id"), 128)
    if raw_id:
        basis = raw_id
    else:
        basis = "|".join(
            str(_get(doc, key) or "")
            for key in ("@timestamp", "src_ip", "src_port", "dest_port", "type", "eventid", "session")
        )
    return hashlib.sha256(basis.encode()).hexdigest()[:20]


def normalize_document(doc: Any, raw_source_type: str = "tpot") -> AttackEvent:
    """Convert one raw T-Pot style document into an ``AttackEvent``.

    Never raises on bad input: non-dict input produces a minimal "other" event.
    """
    if not isinstance(doc, dict):
        doc = {}
    # Elasticsearch hits wrap the document in ``_source``.
    if isinstance(doc.get("_source"), dict):
        merged = dict(doc["_source"])
        merged.setdefault("_id", doc.get("_id"))
        doc = merged

    honeypot = _text(_get(doc, "type", "honeypot"), 64) or "unknown"
    dest_port = _int(_get(doc, "dest_port", "destination_port"), 0, 65535)
    protocol = _text(_get(doc, "protocol", "proto", "app_proto", "connection.protocol"), 32)
    if protocol is None and dest_port is not None:
        service = service_for_port(dest_port)
        protocol = service.lower() if service else None

    return AttackEvent(
        id=_stable_id(doc),
        timestamp=parse_timestamp(_get(doc, "@timestamp", "timestamp")),
        source_ip=_ip(_get(doc, "src_ip", "source_ip")),
        source_latitude=_float(_get(doc, "geoip.latitude", "geoip.location.lat"), -90, 90),
        source_longitude=_float(_get(doc, "geoip.longitude", "geoip.location.lon"), -180, 180),
        source_country=_text(_get(doc, "geoip.country_name"), 64),
        source_country_code=_text(_get(doc, "geoip.country_code2", "geoip.country_iso_code"), 2),
        source_city=_text(_get(doc, "geoip.city_name"), 64),
        source_asn=_int(_get(doc, "geoip.asn", "geoip_ext.asn"), 0, 4_294_967_295),
        source_organization=_text(_get(doc, "geoip.as_org", "geoip_ext.as_org"), 128),
        destination_ip=_ip(_get(doc, "dest_ip", "t-pot_ip_ext", "destination_ip")),
        destination_port=dest_port,
        protocol=protocol.lower() if protocol else None,
        honeypot=honeypot,
        username=_text(_get(doc, "username", "user"), 64),
        password=_text(_get(doc, "password"), 64),
        command=_text(_get(doc, "input", "command")),
        event_type=_event_type(doc, honeypot),
        raw_source_type=raw_source_type,
        raw={k: v for k, v in doc.items() if not k.startswith("_")},
    )
