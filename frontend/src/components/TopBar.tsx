import { useEffect, useState } from "react";

import type { StatusIndicator } from "../hooks/connection";
import type { View } from "../hooks/dashboardState";

interface Props {
  status: StatusIndicator;
  isDemo: boolean;
  publicMode: boolean;
  view: View;
  onViewChange: (view: View) => void;
}

function useClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return now;
}

export function TopBar({ status, isDemo, publicMode, view, onViewChange }: Props) {
  const now = useClock();
  return (
    <header className="topbar">
      <div className="brand">
        <svg className="brand-mark" viewBox="0 0 32 32" aria-hidden>
          <circle cx="16" cy="16" r="13" fill="none" stroke="currentColor" strokeWidth="2" />
          <ellipse cx="16" cy="16" rx="6" ry="13" fill="none" stroke="currentColor" strokeWidth="1.4" />
          <path d="M3 16h26" stroke="currentColor" strokeWidth="1.4" />
          <circle cx="23" cy="10" r="3" fill="#e2602a" />
        </svg>
        <div>
          <div className="brand-name">ThreatGlobe</div>
          <div className="brand-sub">Honeypot Attack Intelligence</div>
        </div>
      </div>

      <div className="topbar-center">
        <div className="segmented" role="tablist" aria-label="Data view">
          <button role="tab" aria-selected={view === "live"} className={view === "live" ? "active" : ""} onClick={() => onViewChange("live")}>
            Live stream
          </button>
          <button role="tab" aria-selected={view === "replay"} className={view === "replay" ? "active" : ""} onClick={() => onViewChange("replay")}>
            Replay
          </button>
        </div>
      </div>

      <div className="topbar-right">
        {isDemo && (
          <span className="badge badge-demo" title="Synthetic, sanitized telemetry — not real attacks">
            DEMO DATA
          </span>
        )}
        {publicMode && (
          <span className="badge badge-muted" title="IPs and passwords are masked">
            PUBLIC MODE
          </span>
        )}
        <span className={`status status-${status.toLowerCase()}`} data-testid="status-indicator" role="status">
          <span className="status-dot" aria-hidden />
          {status}
        </span>
        <time className="clock mono">{now.toISOString().slice(11, 19)} UTC</time>
      </div>
    </header>
  );
}
