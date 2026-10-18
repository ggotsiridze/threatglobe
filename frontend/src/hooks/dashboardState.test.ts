import { describe, expect, it } from "vitest";

import { makeEvent, makeHello, makeSnapshot } from "../test/fixtures";
import { FEED_LIMIT, dashboardReducer, initialDashboard } from "./dashboardState";

describe("dashboardReducer", () => {
  it("hello seeds stats, sensor and a newest-first feed", () => {
    const a = makeEvent();
    const b = makeEvent();
    const s = dashboardReducer(initialDashboard, { type: "hello", hello: makeHello([a, b]) });
    expect(s.sensor?.city).toBe("Frankfurt");
    expect(s.stats?.events_today).toBe(1234);
    expect(s.liveFeed.map((e) => e.id)).toEqual([b.id, a.id]);
  });

  it("attack prepends, bumps counters and ignores an immediate duplicate", () => {
    let s = dashboardReducer(initialDashboard, { type: "hello", hello: makeHello() });
    const e = makeEvent({ severity: "CRITICAL" });
    s = dashboardReducer(s, { type: "attack", event: e });
    s = dashboardReducer(s, { type: "attack", event: e });
    expect(s.liveFeed).toHaveLength(1);
    expect(s.stats?.events_today).toBe(1236);
    expect(s.stats?.severity_counts.CRITICAL).toBe(3);
    expect(s.liveReceived).toBe(2);
  });

  it("feed is bounded", () => {
    let s = initialDashboard;
    for (let i = 0; i < FEED_LIMIT + 25; i++) s = dashboardReducer(s, { type: "attack", event: makeEvent() });
    expect(s.liveFeed).toHaveLength(FEED_LIMIT);
    expect(s.stats).toBeNull(); // no crash before hello
  });

  it("snapshot replaces stats with the authoritative server values", () => {
    let s = dashboardReducer(initialDashboard, { type: "hello", hello: makeHello() });
    s = dashboardReducer(s, { type: "attack", event: makeEvent() });
    s = dashboardReducer(s, { type: "snapshot", snapshot: makeSnapshot(5000) });
    expect(s.stats?.events_today).toBe(5000);
  });

  it("replay feed is separate from the live feed", () => {
    let s = dashboardReducer(initialDashboard, { type: "replayEmit", event: makeEvent() });
    expect(s.replayFeed).toHaveLength(1);
    expect(s.liveFeed).toHaveLength(0);
    s = dashboardReducer(s, { type: "replayReset" });
    expect(s.replayFeed).toHaveLength(0);
    s = dashboardReducer(s, { type: "setView", view: "replay" });
    expect(s.view).toBe("replay");
  });
});
