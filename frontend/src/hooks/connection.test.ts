import { describe, expect, it } from "vitest";

import { backoffDelay, statusIndicator } from "./connection";

describe("statusIndicator", () => {
  it("maps transport + source to the four indicators", () => {
    expect(statusIndicator("open", "demo")).toBe("DEMO");
    expect(statusIndicator("open", "live")).toBe("LIVE");
    expect(statusIndicator("open", null)).toBe("DEMO");
    expect(statusIndicator("connecting", "demo")).toBe("RECONNECTING");
    expect(statusIndicator("reconnecting", "live")).toBe("RECONNECTING");
    expect(statusIndicator("offline", "demo")).toBe("OFFLINE");
  });
});

describe("backoffDelay", () => {
  it("grows exponentially and caps at 15s", () => {
    const mid = () => 0.5;
    expect(backoffDelay(0, mid)).toBe(500);
    expect(backoffDelay(1, mid)).toBe(1000);
    expect(backoffDelay(3, mid)).toBe(4000);
    expect(backoffDelay(20, mid)).toBe(15000);
  });
  it("applies ±20% jitter", () => {
    expect(backoffDelay(1, () => 0)).toBe(800);
    expect(backoffDelay(1, () => 1)).toBe(1200);
  });
});
