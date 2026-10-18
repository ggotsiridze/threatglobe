import type { SourceMode } from "../api/types";

export type ConnectionState = "connecting" | "open" | "reconnecting" | "offline";
export type StatusIndicator = "DEMO" | "LIVE" | "RECONNECTING" | "OFFLINE";

/** Map transport state + data source to the four user-facing indicators. */
export function statusIndicator(conn: ConnectionState, mode: SourceMode | null): StatusIndicator {
  if (conn === "open") return mode === "live" ? "LIVE" : "DEMO";
  if (conn === "offline") return "OFFLINE";
  return "RECONNECTING";
}

/** Exponential backoff with jitter: 0.5s, 1s, 2s … capped at 15s. */
export function backoffDelay(attempt: number, random: () => number = Math.random): number {
  const base = Math.min(15_000, 500 * 2 ** Math.max(0, attempt));
  return Math.round(base * (0.8 + random() * 0.4));
}

/** After this many consecutive failures the UI shows OFFLINE (retries continue). */
export const OFFLINE_AFTER_ATTEMPTS = 4;
