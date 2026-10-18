import type { AttackEvent, Hello, Sensor, Snapshot, Stats, Timeline } from "../api/types";

export const FEED_LIMIT = 120;
export type View = "live" | "replay";

export interface DashboardState {
  sensor: Sensor | null;
  publicMode: boolean;
  stats: Stats | null;
  timeline: Timeline | null;
  liveFeed: AttackEvent[]; // newest first
  replayFeed: AttackEvent[]; // newest first
  view: View;
  liveReceived: number;
}

export type DashboardAction =
  | { type: "hello"; hello: Hello }
  | { type: "attack"; event: AttackEvent }
  | { type: "snapshot"; snapshot: Snapshot }
  | { type: "replayEmit"; event: AttackEvent }
  | { type: "replayReset" }
  | { type: "setView"; view: View };

export const initialDashboard: DashboardState = {
  sensor: null,
  publicMode: true,
  stats: null,
  timeline: null,
  liveFeed: [],
  replayFeed: [],
  view: "live",
  liveReceived: 0,
};

function prepend(feed: AttackEvent[], event: AttackEvent): AttackEvent[] {
  if (feed.length && feed[0].id === event.id) return feed;
  const next = [event, ...feed];
  return next.length > FEED_LIMIT ? next.slice(0, FEED_LIMIT) : next;
}

/** Bump headline counters between authoritative server snapshots. */
function bumpStats(stats: Stats | null, event: AttackEvent): Stats | null {
  if (!stats) return stats;
  return {
    ...stats,
    events_today: stats.events_today + 1,
    events_last_minute: stats.events_last_minute + 1,
    severity_counts: {
      ...stats.severity_counts,
      [event.severity]: (stats.severity_counts[event.severity] ?? 0) + 1,
    },
  };
}

export function dashboardReducer(state: DashboardState, action: DashboardAction): DashboardState {
  switch (action.type) {
    case "hello": {
      const { hello } = action;
      return {
        ...state,
        sensor: hello.sensor,
        publicMode: hello.public_mode,
        stats: hello.snapshot.stats,
        timeline: hello.snapshot.timeline,
        // `recent` arrives oldest-first; feed is newest-first.
        liveFeed: [...hello.recent].reverse().slice(0, FEED_LIMIT),
      };
    }
    case "attack":
      return {
        ...state,
        liveFeed: prepend(state.liveFeed, action.event),
        stats: bumpStats(state.stats, action.event),
        liveReceived: state.liveReceived + 1,
      };
    case "snapshot":
      return { ...state, stats: action.snapshot.stats, timeline: action.snapshot.timeline };
    case "replayEmit":
      return { ...state, replayFeed: prepend(state.replayFeed, action.event) };
    case "replayReset":
      return { ...state, replayFeed: [] };
    case "setView":
      return { ...state, view: action.view };
    default:
      return state;
  }
}
