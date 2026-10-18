import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { makeEvent, makeSnapshot } from "../test/fixtures";
import { AttackDrawer } from "./AttackDrawer";
import { LiveFeed } from "./LiveFeed";
import { ReplayControls } from "./ReplayControls";
import { StatCards } from "./StatCards";
import { TopList } from "./TopList";

describe("StatCards", () => {
  it("shows placeholders before data and values after", () => {
    const { rerender } = render(<StatCards stats={null} />);
    expect(screen.getByTestId("stat-events")).toHaveTextContent("—");
    rerender(<StatCards stats={makeSnapshot(26205).stats} />);
    expect(screen.getByTestId("stat-events")).toHaveTextContent("26,205");
    expect(screen.getByTestId("stat-service")).toHaveTextContent("SSH");
    expect(screen.getByTestId("stat-countries")).toHaveTextContent("37");
  });
});

describe("TopList", () => {
  it("renders ranked items and an empty state", () => {
    const { rerender } = render(<TopList title="Top Ports" items={[]} />);
    expect(screen.getByText("No data yet")).toBeInTheDocument();
    rerender(<TopList title="Top Ports" items={[{ key: "22", label: "22 · SSH", count: 1466 }]} />);
    expect(screen.getByText("22 · SSH")).toBeInTheDocument();
    expect(screen.getByText("1,466")).toBeInTheDocument();
  });
});

describe("LiveFeed", () => {
  it("lists events and reports clicks", () => {
    const onSelect = vi.fn();
    const e = makeEvent({ source_city: "Seoul", source_country: "South Korea", severity: "HIGH" });
    render(<LiveFeed events={[e]} title="Live Attack Feed" selectedId={null} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("feed-item"));
    expect(onSelect).toHaveBeenCalledWith(e);
    expect(screen.getByText("Seoul, South Korea")).toBeInTheDocument();
    expect(screen.getByText("HIGH")).toBeInTheDocument();
  });

  it("renders events with every optional field missing", () => {
    const e = makeEvent({
      source_ip: null, source_latitude: null, source_longitude: null, source_country: null,
      source_country_code: null, source_city: null, destination_port: null, protocol: null,
    });
    render(<LiveFeed events={[e]} title="Feed" selectedId={null} onSelect={() => {}} />);
    expect(screen.getByText("Unknown location")).toBeInTheDocument();
  });
});

describe("AttackDrawer", () => {
  it("shows every required detail with masked values and risk reasons", () => {
    const onClose = vi.fn();
    render(<AttackDrawer event={makeEvent({ command: "uname -a" })} publicMode onClose={onClose} />);
    const drawer = screen.getByTestId("attack-drawer");
    for (const label of ["Timestamp", "Source IP", "Country", "City", "ASN", "Organization", "Protocol",
      "Target port", "Honeypot", "Username", "Password", "Event type"]) {
      expect(drawer).toHaveTextContent(label);
    }
    expect(drawer).toHaveTextContent("203.0.*.*");
    expect(drawer).toHaveTextContent("h••••••");
    expect(drawer).toHaveTextContent("AS64600");
    expect(drawer).toHaveTextContent("MEDIUM");
    expect(drawer).toHaveTextContent("Login attempted as privileged account 'root'");
    expect(drawer).toHaveTextContent("uname -a");
    expect(drawer).toHaveTextContent("not AI");
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("renders nothing without an event and dashes for missing fields", () => {
    const { container, rerender } = render(<AttackDrawer event={null} publicMode onClose={() => {}} />);
    expect(container).toBeEmptyDOMElement();
    rerender(<AttackDrawer event={makeEvent({ source_asn: null, username: null, risk_factors: [] })} publicMode onClose={() => {}} />);
    expect(screen.getByText("No risk rules matched — routine background noise.")).toBeInTheDocument();
  });
});

describe("ReplayControls", () => {
  it("wires play/pause/restart/speed handlers", () => {
    const h = { onPlay: vi.fn(), onPause: vi.fn(), onRestart: vi.fn(), onSpeed: vi.fn(), onMinutes: vi.fn() };
    const state = { status: "idle" as const, speed: 1 as const, index: 3, total: 10, cursor: null };
    const { rerender } = render(<ReplayControls state={state} loading={false} minutes={15} {...h} />);
    fireEvent.click(screen.getByTestId("replay-play"));
    fireEvent.click(screen.getByTestId("replay-restart"));
    fireEvent.click(screen.getByText("5x"));
    fireEvent.change(screen.getByLabelText("Replay window"), { target: { value: "60" } });
    expect(h.onPlay).toHaveBeenCalled();
    expect(h.onRestart).toHaveBeenCalled();
    expect(h.onSpeed).toHaveBeenCalledWith(5);
    expect(h.onMinutes).toHaveBeenCalledWith(60);
    expect(screen.getByTestId("replay-position")).toHaveTextContent("3/10");
    rerender(<ReplayControls state={{ ...state, status: "playing" }} loading={false} minutes={15} {...h} />);
    fireEvent.click(screen.getByTestId("replay-pause"));
    expect(h.onPause).toHaveBeenCalled();
  });
});
