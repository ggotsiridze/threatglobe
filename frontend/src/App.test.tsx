import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { makeEvent, makeHello } from "./test/fixtures";

// WebGL is unavailable in jsdom; the globe is exercised in the browser e2e test.
vi.mock("./components/GlobeView", () => ({
  default: ({ arcs }: { arcs: unknown[] }) => <div data-testid="globe" data-arcs={arcs.length} />,
}));

class FakeSocket {
  static instances: FakeSocket[] = [];
  static OPEN = 1;
  readyState = 0;
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];
  constructor(public url: string) {
    FakeSocket.instances.push(this);
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.readyState = 3;
    this.onclose?.();
  }
  open() {
    this.readyState = 1;
    this.onopen?.();
  }
  push(msg: unknown) {
    this.onmessage?.({ data: JSON.stringify(msg) });
  }
}

describe("App (integration with a fake WebSocket)", () => {
  beforeEach(() => {
    FakeSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeSocket);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("renders hello data, streams attacks, opens details and shows reconnecting", async () => {
    render(<App />);
    const ws = FakeSocket.instances.at(-1)!;
    expect(ws.url).toMatch(/\/ws\/attacks$/);
    expect(screen.getByTestId("status-indicator")).toHaveTextContent("RECONNECTING");

    act(() => {
      ws.open();
      ws.push({ type: "hello", data: makeHello([makeEvent({ source_city: "Lagos", source_country: "Nigeria" })]) });
    });
    expect(screen.getByTestId("status-indicator")).toHaveTextContent("DEMO");
    expect(screen.getAllByText("DEMO DATA").length).toBeGreaterThan(0);
    expect(screen.getByTestId("stat-events")).toHaveTextContent("1,234");
    expect(screen.getByText("Lagos, Nigeria")).toBeInTheDocument();
    expect(await screen.findByTestId("globe")).toBeInTheDocument();

    act(() => ws.push({ type: "attack", data: makeEvent({ source_city: "Lima", source_country: "Peru", severity: "CRITICAL" }) }));
    expect(screen.getByText("Lima, Peru")).toBeInTheDocument();
    expect(screen.getByTestId("stat-events")).toHaveTextContent("1,235");
    expect(screen.getByTestId("globe").dataset.arcs).toBe("1");

    fireEvent.click(screen.getAllByTestId("feed-item")[0]);
    expect(screen.getByTestId("attack-drawer")).toHaveTextContent("Peru");

    act(() => ws.push({ type: "garbage-that-is-ignored" }));
    act(() => ws.onmessage?.({ data: "{not json" }));

    act(() => ws.close());
    expect(screen.getByTestId("status-indicator")).toHaveTextContent("RECONNECTING");
  });
});
