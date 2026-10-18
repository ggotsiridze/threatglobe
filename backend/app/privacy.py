"""PUBLIC_MODE privacy projection.

Events are stored unmasked internally (risk scoring needs real source
identity), and masked at the API boundary. When ``public_mode`` is on:

* source IPs keep only their network prefix (``203.0.*.*``)
* attempted passwords are replaced with a fixed-length mask (length not leaked)
* the honeypot's own destination IP is removed entirely
* IP addresses and URLs inside attacker commands are masked / defanged
* raw source documents are dropped
"""

from __future__ import annotations

import ipaddress
import re

from .models import AttackEvent

PASSWORD_MASK = "••••••"
_IPV4_IN_TEXT = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.\d{1,3}\.\d{1,3}\b")
_URL_SCHEME = re.compile(r"\b(https?|ftp)://", re.IGNORECASE)


def mask_ip(ip: str | None) -> str | None:
    if not ip:
        return ip
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return "masked"
    if addr.version == 4:
        a, b, _, _ = str(addr).split(".")
        return f"{a}.{b}.*.*"
    hextets = addr.exploded.split(":")
    return f"{hextets[0]}:{hextets[1]}:*:*:*:*:*:*"


def mask_password(password: str | None) -> str | None:
    if not password:
        return password
    return f"{password[0]}{PASSWORD_MASK}"


def sanitize_command(command: str | None) -> str | None:
    if not command:
        return command
    masked = _IPV4_IN_TEXT.sub(lambda m: f"{m.group(1)}.{m.group(2)}.*.*", command)
    # Defang URLs so nothing in the UI is a clickable malware link.
    return _URL_SCHEME.sub(lambda m: m.group(1).lower().replace("t", "x", 2) + "[:]//", masked)


def project_event(event: AttackEvent, public_mode: bool) -> dict:
    """Return the JSON-ready representation of ``event`` for API clients."""
    if not public_mode:
        return event.model_dump(mode="json")
    data = event.model_dump(mode="json", exclude={"raw"})
    data["source_ip"] = mask_ip(event.source_ip)
    data["password"] = mask_password(event.password)
    data["destination_ip"] = None
    data["command"] = sanitize_command(event.command)
    data["raw"] = None
    return data
