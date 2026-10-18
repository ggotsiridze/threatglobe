import type { AttackEvent, EventType, Severity } from "../api/types";

export const SEVERITY_COLORS: Record<Severity, string> = {
  LOW: "#3d8fe0",
  MEDIUM: "#c7a41a",
  HIGH: "#e2602a",
  CRITICAL: "#c22d8a",
};

const EVENT_LABELS: Record<EventType, string> = {
  connection: "Connection",
  scan: "Port scan",
  login_attempt: "Login attempt",
  login_success: "Login success",
  command: "Command execution",
  malware: "Malware",
  exploit: "Exploit attempt",
  web_request: "Web probe",
  other: "Other",
};

export function eventTypeLabel(type: EventType | string | null | undefined): string {
  return (type && EVENT_LABELS[type as EventType]) || "Unknown";
}

const nf = new Intl.NumberFormat("en-US");
export const formatNumber = (n: number | null | undefined): string => (n == null ? "—" : nf.format(n));

export function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toISOString().slice(11, 19);
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return `${d.toISOString().slice(0, 10)} ${d.toISOString().slice(11, 19)} UTC`;
}

/** ISO 3166 alpha-2 → regional-indicator flag emoji. */
export function flag(code: string | null | undefined): string {
  if (!code || !/^[A-Za-z]{2}$/.test(code)) return "🏳";
  return String.fromCodePoint(...[...code.toUpperCase()].map((c) => 0x1f1a5 + c.charCodeAt(0)));
}

export function locationLabel(e: Pick<AttackEvent, "source_city" | "source_country">): string {
  return [e.source_city, e.source_country].filter(Boolean).join(", ") || "Unknown location";
}

export function serviceLabel(e: Pick<AttackEvent, "protocol" | "destination_port">): string {
  const proto = e.protocol ? e.protocol.toUpperCase() : null;
  const port = e.destination_port != null ? `:${e.destination_port}` : "";
  return proto ? `${proto}${port}` : port ? `port${port}` : "—";
}

export const orDash = (v: string | number | null | undefined): string =>
  v === null || v === undefined || v === "" ? "—" : String(v);
