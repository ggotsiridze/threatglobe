from datetime import UTC, datetime, timedelta

from app.models import AttackEvent, Severity
from app.store import EventStore

NOW = datetime(2026, 1, 15, 12, 30, tzinfo=UTC)


def ev(i, minutes_ago, **kw):
    return AttackEvent(id=f"e{i}", timestamp=NOW - timedelta(minutes=minutes_ago), **kw)


def test_query_order_filters_and_limit():
    s = EventStore()
    s.add(ev(1, 30, source_country_code="CN", destination_port=22, honeypot="Cowrie"))
    s.add(ev(2, 20, source_country_code="US", destination_port=80, honeypot="Tanner", severity=Severity.HIGH))
    s.add(ev(3, 10, source_country_code="CN", destination_port=22, honeypot="Cowrie"))
    assert [e.id for e in s.query()] == ["e3", "e2", "e1"]
    assert [e.id for e in s.query(order="asc")] == ["e1", "e2", "e3"]
    assert [e.id for e in s.query(country="cn")] == ["e3", "e1"]
    assert [e.id for e in s.query(port=80)] == ["e2"]
    assert [e.id for e in s.query(severity=Severity.HIGH)] == ["e2"]
    assert [e.id for e in s.query(honeypot="cowrie", limit=1)] == ["e3"]
    assert [e.id for e in s.query(since=NOW - timedelta(minutes=15))] == ["e3"]


def test_eviction_and_duplicates():
    s = EventStore(max_events=2)
    for i in range(3):
        s.add(ev(i, 10 - i))
    s.add(ev(2, 0))  # duplicate id ignored
    assert len(s) == 2 and s.get("e0") is None and s.get("e2") is not None


def test_out_of_order_insert_keeps_chronology_even_when_full():
    s = EventStore(max_events=3)
    s.add(ev(1, 30))
    s.add(ev(2, 10))
    s.add(ev(3, 5))
    s.add(ev(4, 20))  # late arrival into a full buffer
    assert [e.id for e in s.query(order="asc")] == ["e4", "e2", "e3"]


def test_stats_and_top_lists():
    s = EventStore()
    s.add(ev(1, 120, source_ip="203.0.113.1", source_country_code="CN", source_country="China", destination_port=22))
    s.add(ev(2, 60, source_ip="203.0.113.1", source_country_code="CN", source_country="China", destination_port=22))
    s.add(ev(3, 0.5, source_ip="198.51.100.2", source_country_code="US", source_country="United States",
             destination_port=80, honeypot="Tanner", severity=Severity.CRITICAL))  # fmt: skip
    s.add(ev(4, 60 * 30, source_ip="192.0.2.9", destination_port=23))  # outside 24h window
    st = s.stats(24, now=NOW)
    assert st.events_today == 3
    assert st.unique_source_ips == 2
    assert st.countries_observed == 2
    assert st.most_targeted_service == "SSH"
    assert st.events_last_minute == 1
    assert st.severity_counts == {"LOW": 2, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 1}
    assert st.top_countries[0].key == "CN" and st.top_countries[0].count == 2
    assert st.top_ports[0].label == "22 · SSH"


def test_missing_fields_in_aggregations():
    s = EventStore()
    s.add(ev(1, 1))
    st = s.stats(24, now=NOW)
    assert st.events_today == 1 and st.most_targeted_service is None
    assert s.countries(now=NOW)[0].label == "Unknown"
    assert s.ports(now=NOW) == []


def test_timeline_buckets():
    s = EventStore()
    s.add(ev(1, 5, severity=Severity.HIGH))
    s.add(ev(2, 65))
    s.add(ev(3, 66, severity=Severity.CRITICAL))
    tl = s.timeline(hours=3, bucket_minutes=60, now=NOW)
    assert len(tl.buckets) == 3
    assert sum(b.total for b in tl.buckets) == 3
    last = tl.buckets[-1]
    assert last.start == datetime(2026, 1, 15, 12, tzinfo=UTC) and last.high == 1
    assert tl.buckets[-2].critical == 1 and tl.buckets[-2].low == 1
