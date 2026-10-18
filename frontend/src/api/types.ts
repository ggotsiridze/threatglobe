// Mirrors backend/app/models.py. Every field except id/timestamp may be null.

export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export const SEVERITIES: Severity[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

export type EventType =
  | "connection"
  | "scan"
  | "login_attempt"
  | "login_success"
  | "command"
  | "malware"
  | "exploit"
  | "web_request"
  | "other";

export interface RiskFactor {
  rule: string;
  points: number;
  detail: string;
}

export interface AttackEvent {
  id: string;
  timestamp: string;
  source_ip: string | null;
  source_latitude: number | null;
  source_longitude: number | null;
  source_country: string | null;
  source_country_code: string | null;
  source_city: string | null;
  source_asn: number | null;
  source_organization: string | null;
  destination_ip: string | null;
  destination_port: number | null;
  protocol: string | null;
  honeypot: string;
  username: string | null;
  password: string | null;
  command: string | null;
  event_type: EventType;
  severity: Severity;
  risk_score: number;
  risk_factors: RiskFactor[];
  raw_source_type: string;
}

export interface CountStat {
  key: string;
  label: string;
  count: number;
}

export interface Stats {
  events_today: number;
  unique_source_ips: number;
  countries_observed: number;
  most_targeted_service: string | null;
  events_last_minute: number;
  severity_counts: Record<Severity, number>;
  top_countries: CountStat[];
  top_ports: CountStat[];
  top_honeypots: CountStat[];
  window_hours: number;
  generated_at: string;
}

export interface TimelineBucket {
  start: string;
  total: number;
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export interface Timeline {
  bucket_minutes: number;
  buckets: TimelineBucket[];
}

export interface Snapshot {
  stats: Stats;
  timeline: Timeline;
}

export interface Sensor {
  name: string;
  latitude: number;
  longitude: number;
  city: string;
  country: string;
}

export type SourceMode = "demo" | "live";

export interface Hello {
  mode: SourceMode;
  public_mode: boolean;
  sensor: Sensor;
  recent: AttackEvent[];
  snapshot: Snapshot;
}

export type ServerMessage =
  | { type: "hello"; data: Hello }
  | { type: "attack"; data: AttackEvent }
  | { type: "snapshot"; data: Snapshot }
  | { type: "pong" };
