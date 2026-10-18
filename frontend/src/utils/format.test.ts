import { describe, expect, it } from "vitest";

import { eventTypeLabel, flag, formatDateTime, formatNumber, formatTime, locationLabel, orDash, serviceLabel } from "./format";

describe("format helpers", () => {
  it("renders flags and tolerates bad codes", () => {
    expect(flag("CN")).toBe("🇨🇳");
    expect(flag("us")).toBe("🇺🇸");
    expect(flag(null)).toBe("🏳");
    expect(flag("??")).toBe("🏳");
  });
  it("handles missing location and service fields", () => {
    expect(locationLabel({ source_city: null, source_country: null })).toBe("Unknown location");
    expect(locationLabel({ source_city: null, source_country: "Brazil" })).toBe("Brazil");
    expect(serviceLabel({ protocol: "ssh", destination_port: 22 })).toBe("SSH:22");
    expect(serviceLabel({ protocol: null, destination_port: 445 })).toBe("port:445");
    expect(serviceLabel({ protocol: null, destination_port: null })).toBe("—");
  });
  it("formats numbers, times and blanks", () => {
    expect(formatNumber(26205)).toBe("26,205");
    expect(formatNumber(undefined)).toBe("—");
    expect(formatTime("2026-01-15T10:00:05Z")).toBe("10:00:05");
    expect(formatTime("garbage")).toBe("—");
    expect(formatDateTime("2026-01-15T10:00:05Z")).toBe("2026-01-15 10:00:05 UTC");
    expect(orDash("")).toBe("—");
    expect(orDash(0)).toBe("0");
    expect(eventTypeLabel("malware")).toBe("Malware");
    expect(eventTypeLabel("unknown-type")).toBe("Unknown");
  });
});
