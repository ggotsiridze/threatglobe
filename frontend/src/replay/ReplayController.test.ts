import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { makeEvent } from "../test/fixtures";
import { ReplayController } from "./ReplayController";

const at = (sec: number, id: string) => makeEvent({ id, timestamp: new Date(Date.UTC(2026, 0, 1, 0, 0, sec)).toISOString() });

describe("ReplayController", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("emits events in chronological order even when loaded unsorted, keeping ties stable", () => {
    const emitted: string[] = [];
    const c = new ReplayController((e) => emitted.push(e.id));
    c.load([at(5, "c"), at(1, "a"), at(3, "b1"), at(3, "b2"), makeEvent({ id: "bad", timestamp: "not-a-date" })]);
    expect(c.state.total).toBe(4);
    c.play();
    vi.runAllTimers();
    expect(emitted).toEqual(["a", "b1", "b2", "c"]);
    expect(c.state.status).toBe("finished");
    expect(c.state.index).toBe(4);
  });

  it("1x is real time and higher speeds shorten gaps proportionally", () => {
    const c = new ReplayController(() => {});
    c.load([at(0, "a"), at(1, "b")]);
    expect(c.delayFor(1)).toBe(1000);
    for (const [speed, ms] of [[2, 500], [5, 200], [10, 100]] as const) {
      c.setSpeed(speed);
      expect(c.delayFor(1)).toBe(ms);
    }
  });

  it("caps long quiet gaps", () => {
    const c = new ReplayController(() => {}, { maxGapMs: 2000 });
    c.load([at(0, "a"), at(50, "b")]);
    expect(c.delayFor(1)).toBe(2000);
    c.setSpeed(10);
    expect(c.delayFor(1)).toBe(200);
  });

  it("pause stops emission and play resumes from the same position", () => {
    const emitted: string[] = [];
    const c = new ReplayController((e) => emitted.push(e.id));
    c.load([at(0, "a"), at(1, "b"), at(2, "c")]);
    c.play();
    vi.advanceTimersByTime(0);
    expect(emitted).toEqual(["a"]);
    c.pause();
    vi.advanceTimersByTime(10_000);
    expect(emitted).toEqual(["a"]);
    expect(c.state.status).toBe("paused");
    c.play();
    vi.advanceTimersByTime(1000);
    expect(emitted).toEqual(["a", "b"]);
  });

  it("restart replays from the beginning; play after finish also restarts", () => {
    const emitted: string[] = [];
    const c = new ReplayController((e) => emitted.push(e.id));
    c.load([at(0, "a"), at(1, "b")]);
    c.play();
    vi.runAllTimers();
    c.restart();
    vi.runAllTimers();
    c.play();
    vi.runAllTimers();
    expect(emitted).toEqual(["a", "b", "a", "b", "a", "b"]);
  });

  it("changing speed while playing reschedules the pending event", () => {
    const emitted: string[] = [];
    const c = new ReplayController((e) => emitted.push(e.id));
    c.load([at(0, "a"), at(1, "b")]);
    c.play();
    vi.advanceTimersByTime(0);
    c.setSpeed(10);
    vi.advanceTimersByTime(100);
    expect(emitted).toEqual(["a", "b"]);
  });

  it("does nothing when there is no data and notifies subscribers", () => {
    const states: string[] = [];
    const c = new ReplayController(() => {});
    c.subscribe((s) => states.push(s.status));
    c.play();
    expect(c.state.status).toBe("idle");
    c.load([at(0, "a")]);
    c.play();
    vi.runAllTimers();
    expect(states).toContain("playing");
    expect(states.at(-1)).toBe("finished");
  });
});
