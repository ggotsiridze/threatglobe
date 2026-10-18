"""Bounded in-memory event store with dashboard aggregations.

Storage is a ring buffer ordered by insertion (which is chronological, since
the pipeline processes events in order). A real deployment would query
Elasticsearch for long-range history; this store holds the hot window that
drives the live dashboard.
"""

from __future__ import annotations

from bisect import bisect_left
from collections import Counter, deque
from datetime import UTC, datetime, timedelta

from .models import AttackEvent, CountStat, Severity, StatsSnapshot, Timeline, TimelineBucket
from .normalize import service_for_port


class EventStore:
    def __init__(self, max_events: int = 50_000) -> None:
        self._events: deque[AttackEvent] = deque(maxlen=max_events)
        self._by_id: dict[str, AttackEvent] = {}

    def __len__(self) -> int:
        return len(self._events)

    def clear(self) -> None:
        self._events.clear()
        self._by_id.clear()

    def add(self, event: AttackEvent) -> None:
        if event.id in self._by_id:
            return
        if self._events.maxlen and len(self._events) == self._events.maxlen:
            evicted = self._events.popleft()
            self._by_id.pop(evicted.id, None)
        if self._events and event.timestamp < self._events[-1].timestamp:
            # Late/out-of-order event: keep the buffer sorted (rare, O(n)).
            idx = bisect_left(self._events, event.timestamp, key=lambda e: e.timestamp)
            self._events.insert(idx, event)
        else:
            self._events.append(event)
        self._by_id[event.id] = event

    def get(self, event_id: str) -> AttackEvent | None:
        return self._by_id.get(event_id)

    def _since(self, start: datetime) -> list[AttackEvent]:
        events = list(self._events)
        idx = bisect_left(events, start, key=lambda e: e.timestamp)
        return events[idx:]

    def query(
        self,
        *,
        limit: int = 100,
        since: datetime | None = None,
        until: datetime | None = None,
        severity: Severity | None = None,
        country: str | None = None,
        honeypot: str | None = None,
        port: int | None = None,
        order: str = "desc",
    ) -> list[AttackEvent]:
        events = self._since(since) if since else list(self._events)
        if order == "desc":
            events.reverse()
        results: list[AttackEvent] = []
        for event in events:
            if until and event.timestamp > until:
                continue
            if severity and event.severity != severity:
                continue
            if country and (event.source_country_code or "").upper() != country.upper():
                continue
            if honeypot and event.honeypot.lower() != honeypot.lower():
                continue
            if port is not None and event.destination_port != port:
                continue
            results.append(event)
            if len(results) >= limit:
                break
        return results

    # --- aggregations -----------------------------------------------------

    def window(self, hours: int, now: datetime | None = None) -> list[AttackEvent]:
        now = now or datetime.now(UTC)
        return self._since(now - timedelta(hours=hours))

    @staticmethod
    def _top(counter: Counter, labels: dict[str, str], n: int) -> list[CountStat]:
        return [CountStat(key=k, label=labels.get(k, k), count=c) for k, c in counter.most_common(n)]

    def countries(self, hours: int = 24, n: int = 10, now: datetime | None = None) -> list[CountStat]:
        counter: Counter = Counter()
        labels: dict[str, str] = {}
        for e in self.window(hours, now):
            key = e.source_country_code or "??"
            counter[key] += 1
            labels[key] = e.source_country or "Unknown"
        return self._top(counter, labels, n)

    def ports(self, hours: int = 24, n: int = 10, now: datetime | None = None) -> list[CountStat]:
        counter: Counter = Counter()
        labels: dict[str, str] = {}
        for e in self.window(hours, now):
            if e.destination_port is None:
                continue
            key = str(e.destination_port)
            counter[key] += 1
            service = service_for_port(e.destination_port)
            labels[key] = f"{key} · {service}" if service else key
        return self._top(counter, labels, n)

    def honeypots(self, hours: int = 24, n: int = 10, now: datetime | None = None) -> list[CountStat]:
        counter: Counter = Counter(e.honeypot for e in self.window(hours, now))
        return self._top(counter, {}, n)

    def stats(self, hours: int = 24, now: datetime | None = None) -> StatsSnapshot:
        now = now or datetime.now(UTC)
        events = self.window(hours, now)
        minute_ago = now - timedelta(minutes=1)
        services: Counter = Counter()
        for e in events:
            service = service_for_port(e.destination_port)
            if service:
                services[service] += 1
        severity_counts = Counter(e.severity.value for e in events)
        return StatsSnapshot(
            events_today=len(events),
            unique_source_ips=len({e.source_ip for e in events if e.source_ip}),
            countries_observed=len({e.source_country_code for e in events if e.source_country_code}),
            most_targeted_service=services.most_common(1)[0][0] if services else None,
            events_last_minute=sum(1 for e in events if e.timestamp >= minute_ago),
            severity_counts={s.value: severity_counts.get(s.value, 0) for s in Severity},
            top_countries=self.countries(hours, 8, now),
            top_ports=self.ports(hours, 8, now),
            top_honeypots=self.honeypots(hours, 8, now),
            window_hours=hours,
            generated_at=now,
        )

    def timeline(self, hours: int = 24, bucket_minutes: int = 60, now: datetime | None = None) -> Timeline:
        now = now or datetime.now(UTC)
        bucket = timedelta(minutes=bucket_minutes)
        # Rolling buckets ending at ``now``: every bucket is complete, so the
        # newest one never shows a misleading partial-bucket "drop".
        end = now
        count = max(1, int(timedelta(hours=hours) / bucket))
        start = end - count * bucket
        buckets = [TimelineBucket(start=start + i * bucket, total=0) for i in range(count)]
        for e in self._since(start):
            idx = int((e.timestamp - start) / bucket)
            if 0 <= idx < count and e.timestamp < end:
                b = buckets[idx]
                b.total += 1
                level = e.severity.value.lower()
                setattr(b, level, getattr(b, level) + 1)
        return Timeline(bucket_minutes=bucket_minutes, buckets=buckets)
