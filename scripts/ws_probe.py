#!/usr/bin/env python3
"""Minimal stdlib-only WebSocket client used by scripts/verify.sh.

Connects to /ws/attacks, reads frames for a few seconds and prints a JSON
summary: message type counts, whether attack timestamps were chronological,
and whether every source IP was masked.
"""

import base64
import json
import os
import socket
import struct
import sys
import time
from urllib.parse import urlparse


def recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed")
        buf += chunk
    return buf


def read_frame(sock: socket.socket) -> tuple[int, bytes]:
    b1, b2 = recv_exact(sock, 2)
    opcode, length = b1 & 0x0F, b2 & 0x7F
    if length == 126:
        length = struct.unpack(">H", recv_exact(sock, 2))[0]
    elif length == 127:
        length = struct.unpack(">Q", recv_exact(sock, 8))[0]
    return opcode, recv_exact(sock, length)


def main() -> int:
    url = urlparse(sys.argv[1])
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 6
    sock = socket.create_connection((url.hostname, url.port or 80), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall(
        (
            f"GET {url.path} HTTP/1.1\r\nHost: {url.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode()
    )
    header = b""
    while b"\r\n\r\n" not in header:
        header += sock.recv(1)
    if b" 101 " not in header.split(b"\r\n")[0]:
        print(json.dumps({"error": header.split(b"\r\n")[0].decode()}))
        return 1
    counts: dict[str, int] = {}
    stamps: list[str] = []
    masked = True
    deadline = time.time() + seconds
    while time.time() < deadline:
        opcode, payload = read_frame(sock)
        if opcode != 1:
            continue
        msg = json.loads(payload)
        counts[msg["type"]] = counts.get(msg["type"], 0) + 1
        if msg["type"] == "attack":
            stamps.append(msg["data"]["timestamp"])
            ip = msg["data"].get("source_ip")
            masked &= ip is None or ip.endswith("*")
    sock.close()
    print(json.dumps({"counts": counts, "chronological": stamps == sorted(stamps), "masked": masked}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
