import type { AttackEvent } from "./types";

// Same-origin by default: Vite (dev) and nginx (Docker) proxy /api and /ws to
// the backend. The browser never talks to Elasticsearch or any data store.
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export function wsUrl(path = "/ws/attacks"): string {
  const explicit = import.meta.env.VITE_WS_URL as string | undefined;
  if (explicit) return explicit;
  const { protocol, host } = window.location;
  return `${protocol === "https:" ? "wss" : "ws"}://${host}${path}`;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { signal, headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`${path} → HTTP ${res.status}`);
  return (await res.json()) as T;
}

export async function fetchReplayEvents(minutes: number, signal?: AbortSignal): Promise<AttackEvent[]> {
  const since = new Date(Date.now() - minutes * 60_000).toISOString();
  const params = new URLSearchParams({ since, order: "asc", limit: "5000" });
  const body = await getJson<{ events: AttackEvent[] }>(`/api/events?${params}`, signal);
  return body.events;
}

export async function fetchEvent(id: string, signal?: AbortSignal): Promise<AttackEvent> {
  return getJson<AttackEvent>(`/api/events/${encodeURIComponent(id)}`, signal);
}
