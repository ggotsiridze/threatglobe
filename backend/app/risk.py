"""Transparent rule-based risk scoring.

This is NOT machine learning. Each rule adds a fixed number of points and
records a human-readable reason, so the UI can show exactly why an event was
rated the way it was. Scores are capped at 100 and mapped to ratings:

    0-24  LOW   | 25-49 MEDIUM | 50-74 HIGH | 75-100 CRITICAL

The engine is stateful (it remembers recent activity per source IP) and must
be fed events in chronological order; it uses event timestamps rather than
wall-clock time, so scoring historical data is deterministic.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import timedelta

from .models import AttackEvent, EventType, RiskFactor, Severity

PRIVILEGED_USERNAMES = frozenset(
    {
        "root", "admin", "administrator", "sa", "sysadmin", "superuser", "supervisor",
        "oracle", "postgres", "mysql", "ubnt", "pi", "support", "system", "enable",
    }
)  # fmt: skip
REMOTE_SHELL_PROTOCOLS = frozenset({"ssh", "telnet"})
REMOTE_SHELL_PORTS = frozenset({22, 23, 2222, 2223})
ICS_PORTS = frozenset({102, 502, 20000, 44818, 47808})

# Rule weights — kept in one table so they are easy to audit and document.
POINTS = {
    "privileged_username": 20,
    "remote_shell_login": 10,
    "brute_force": 20,
    "login_success": 25,
    "command_execution": 30,
    "malware": 45,
    "exploit_attempt": 25,
    "ics_target": 15,
    "repeated_source": 10,
    "persistent_source": 10,
    "abnormal_frequency": 20,
}

BRUTE_FORCE_WINDOW = timedelta(minutes=10)
BRUTE_FORCE_THRESHOLD = 5
REPEAT_WINDOW = timedelta(hours=1)
REPEAT_THRESHOLD = 10
PERSISTENT_THRESHOLD = 50
BURST_WINDOW = timedelta(seconds=60)
BURST_THRESHOLD = 20


def rating_for_score(score: int) -> Severity:
    if score >= 75:
        return Severity.CRITICAL
    if score >= 50:
        return Severity.HIGH
    if score >= 25:
        return Severity.MEDIUM
    return Severity.LOW


def describe_rules() -> list[dict[str, object]]:
    """Machine-readable rule table, exposed via /api/status for transparency."""
    return [{"rule": name, "points": pts} for name, pts in POINTS.items()]


class RiskEngine:
    def __init__(self) -> None:
        self._activity: dict[str, deque] = defaultdict(deque)
        self._logins: dict[str, deque] = defaultdict(deque)
        self._seen = 0

    def reset(self) -> None:
        self._activity.clear()
        self._logins.clear()

    @staticmethod
    def _prune(window: deque, cutoff) -> None:
        while window and window[0] < cutoff:
            window.popleft()

    def _sweep(self, now) -> None:
        """Forget sources that have gone quiet so memory stays bounded."""
        cutoff = now - REPEAT_WINDOW
        for table in (self._activity, self._logins):
            for key in [k for k, w in table.items() if not w or w[-1] < cutoff]:
                del table[key]

    def score(self, event: AttackEvent) -> AttackEvent:
        """Score ``event`` in place (and return it)."""
        self._seen += 1
        if self._seen % 5000 == 0:
            self._sweep(event.timestamp)
        factors: list[RiskFactor] = []

        def add(rule: str, detail: str) -> None:
            factors.append(RiskFactor(rule=rule, points=POINTS[rule], detail=detail))

        ts = event.timestamp
        is_login = event.event_type in (EventType.LOGIN_ATTEMPT, EventType.LOGIN_SUCCESS)
        remote_shell = (event.protocol or "") in REMOTE_SHELL_PROTOCOLS or (
            event.destination_port in REMOTE_SHELL_PORTS
        )

        if event.username and event.username.lower() in PRIVILEGED_USERNAMES:
            add("privileged_username", f"Login attempted as privileged account '{event.username}'")
        if is_login and remote_shell:
            add("remote_shell_login", "Credential attempt against SSH/Telnet")
        if event.event_type == EventType.LOGIN_SUCCESS:
            add("login_success", "Attacker obtained a (honeypot) shell session")
        if event.event_type == EventType.COMMAND:
            add("command_execution", "Attacker executed commands in the honeypot")
        if event.event_type == EventType.MALWARE:
            add("malware", "Malware download or upload observed")
        if event.event_type == EventType.EXPLOIT:
            add("exploit_attempt", "Exploit or IDS signature match")
        if event.destination_port in ICS_PORTS:
            add("ics_target", f"Industrial control protocol targeted (port {event.destination_port})")

        source = event.source_ip
        if source:
            activity = self._activity[source]
            activity.append(ts)
            self._prune(activity, ts - REPEAT_WINDOW)
            recent = len(activity)
            if recent >= PERSISTENT_THRESHOLD:
                add("persistent_source", f"{recent} events from this source in the last hour")
            if recent >= REPEAT_THRESHOLD:
                add("repeated_source", f"Source seen {recent} times in the last hour")
            burst = sum(1 for t in activity if t >= ts - BURST_WINDOW)
            if burst >= BURST_THRESHOLD:
                add("abnormal_frequency", f"{burst} events from this source within 60 seconds")

            if is_login:
                logins = self._logins[source]
                logins.append(ts)
                self._prune(logins, ts - BRUTE_FORCE_WINDOW)
                if len(logins) >= BRUTE_FORCE_THRESHOLD and remote_shell:
                    add("brute_force", f"{len(logins)} login attempts in 10 minutes (brute force)")

        score = min(100, sum(f.points for f in factors))
        event.risk_score = score
        event.risk_factors = factors
        event.severity = rating_for_score(score)
        return event
