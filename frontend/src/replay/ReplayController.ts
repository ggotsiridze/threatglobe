import type { AttackEvent } from "../api/types";

export type ReplayStatus = "idle" | "playing" | "paused" | "finished";
export const REPLAY_SPEEDS = [1, 2, 5, 10] as const;
export type ReplaySpeed = (typeof REPLAY_SPEEDS)[number];

export interface ReplayState {
  status: ReplayStatus;
  speed: ReplaySpeed;
  index: number; // number of events already emitted
  total: number;
  cursor: string | null; // timestamp of the last emitted event
}

export interface Scheduler {
  setTimeout(fn: () => void, ms: number): unknown;
  clearTimeout(handle: unknown): void;
}

export interface ReplayOptions {
  /** Recorded seconds played per wall-clock second at 1x (default 1 = real time). */
  compression?: number;
  /** Longest wall-clock pause at 1x, so quiet periods don't stall playback. */
  maxGapMs?: number;
  scheduler?: Scheduler;
}

const defaultScheduler: Scheduler = {
  setTimeout: (fn, ms) => globalThis.setTimeout(fn, ms),
  clearTimeout: (h) => globalThis.clearTimeout(h as ReturnType<typeof setTimeout>),
};

/**
 * Plays stored events back in strict chronological order.
 *
 * Inter-event delays are the recorded gaps compressed by ``compression × speed``
 * and capped at ``maxGapMs / speed``. Events are sorted once on load (stable
 * sort, so ties keep server order) and emitted strictly by index.
 */
export class ReplayController {
  private events: AttackEvent[] = [];
  private times: number[] = [];
  private timer: unknown = null;
  private listeners = new Set<(s: ReplayState) => void>();
  private readonly compression: number;
  private readonly maxGapMs: number;
  private readonly scheduler: Scheduler;
  private _state: ReplayState = { status: "idle", speed: 1, index: 0, total: 0, cursor: null };

  constructor(
    private readonly onEmit: (event: AttackEvent) => void,
    options: ReplayOptions = {},
  ) {
    this.compression = options.compression ?? 1;
    this.maxGapMs = options.maxGapMs ?? 2000;
    this.scheduler = options.scheduler ?? defaultScheduler;
  }

  get state(): ReplayState {
    return this._state;
  }

  subscribe(fn: (s: ReplayState) => void): () => void {
    this.listeners.add(fn);
    fn(this._state);
    return () => this.listeners.delete(fn);
  }

  private set(patch: Partial<ReplayState>) {
    this._state = { ...this._state, ...patch };
    this.listeners.forEach((fn) => fn(this._state));
  }

  load(events: AttackEvent[]) {
    this.clearTimer();
    const withTime = events
      .map((e, i) => ({ e, i, t: Date.parse(e.timestamp) }))
      .filter((x) => !Number.isNaN(x.t))
      .sort((a, b) => a.t - b.t || a.i - b.i);
    this.events = withTime.map((x) => x.e);
    this.times = withTime.map((x) => x.t);
    this.set({ status: "idle", index: 0, total: this.events.length, cursor: null });
  }

  /** Wall-clock delay before emitting event ``i`` at the current speed. */
  delayFor(i: number): number {
    if (i <= 0) return 0;
    const gap = Math.max(0, this.times[i] - this.times[i - 1]);
    const speed = this._state.speed;
    return Math.min(gap / (this.compression * speed), this.maxGapMs / speed);
  }

  play() {
    if (this._state.status === "playing" || this.events.length === 0) return;
    if (this._state.status === "finished") {
      this.set({ index: 0, cursor: null });
    }
    this.set({ status: "playing" });
    this.schedule();
  }

  pause() {
    if (this._state.status !== "playing") return;
    this.clearTimer();
    this.set({ status: "paused" });
  }

  restart() {
    this.clearTimer();
    this.set({ index: 0, cursor: null, status: "idle" });
    this.play();
  }

  setSpeed(speed: ReplaySpeed) {
    this.set({ speed });
    if (this._state.status === "playing") {
      this.clearTimer();
      this.schedule();
    }
  }

  dispose() {
    this.clearTimer();
    this.listeners.clear();
  }

  private clearTimer() {
    if (this.timer !== null) {
      this.scheduler.clearTimeout(this.timer);
      this.timer = null;
    }
  }

  private schedule() {
    const i = this._state.index;
    if (i >= this.events.length) {
      this.set({ status: "finished" });
      return;
    }
    this.timer = this.scheduler.setTimeout(() => {
      this.timer = null;
      this.step();
    }, this.delayFor(i));
  }

  private step() {
    if (this._state.status !== "playing") return;
    const i = this._state.index;
    const event = this.events[i];
    this.onEmit(event);
    this.set({ index: i + 1, cursor: event.timestamp });
    this.schedule();
  }
}
