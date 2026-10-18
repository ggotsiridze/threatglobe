import type { AttackEvent, Hello, Snapshot } from "../api/types";

let n = 0;
export function makeEvent(overrides: Partial<AttackEvent> = {}): AttackEvent {
  n += 1;
  return {
    id: `evt-${n}`,
    timestamp: new Date(Date.UTC(2026, 0, 15, 10, 0, n)).toISOString(),
    source_ip: "203.0.*.*",
    source_latitude: 39.9,
    source_longitude: 116.4,
    source_country: "China",
    source_country_code: "CN",
    source_city: "Beijing",
    source_asn: 64600,
    source_organization: "Example Cloud Hosting (CN)",
    destination_ip: null,
    destination_port: 22,
    protocol: "ssh",
    honeypot: "Cowrie",
    username: "root",
    password: "h••••••",
    command: null,
    event_type: "login_attempt",
    severity: "MEDIUM",
    risk_score: 30,
    risk_factors: [
      { rule: "privileged_username", points: 20, detail: "Login attempted as privileged account 'root'" },
      { rule: "remote_shell_login", points: 10, detail: "Credential attempt against SSH/Telnet" },
    ],
    raw_source_type: "demo",
    ...overrides,
  };
}

export function makeSnapshot(eventsToday = 1234): Snapshot {
  return {
    stats: {
      events_today: eventsToday,
      unique_source_ips: 276,
      countries_observed: 37,
      most_targeted_service: "SSH",
      events_last_minute: 70,
      severity_counts: { LOW: 10, MEDIUM: 5, HIGH: 2, CRITICAL: 1 },
      top_countries: [{ key: "CN", label: "China", count: 400 }],
      top_ports: [{ key: "22", label: "22 · SSH", count: 800 }],
      top_honeypots: [{ key: "Cowrie", label: "Cowrie", count: 900 }],
      window_hours: 24,
      generated_at: "2026-01-15T10:00:00Z",
    },
    timeline: { bucket_minutes: 10, buckets: [{ start: "2026-01-15T09:50:00Z", total: 5, low: 2, medium: 1, high: 1, critical: 1 }] },
  };
}

export function makeHello(recent: AttackEvent[] = []): Hello {
  return {
    mode: "demo",
    public_mode: true,
    sensor: { name: "tpot-demo-01", latitude: 50.11, longitude: 8.68, city: "Frankfurt", country: "Germany" },
    recent,
    snapshot: makeSnapshot(),
  };
}
