import { useEffect } from "react";

import type { AttackEvent } from "../api/types";
import { eventTypeLabel, flag, formatDateTime, orDash } from "../utils/format";
import { SeverityBadge } from "./SeverityBadge";

interface Props {
  event: AttackEvent | null;
  publicMode: boolean;
  onClose: () => void;
}

export function AttackDrawer({ event, publicMode, onClose }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!event) return null;
  const rows: [string, string][] = [
    ["Timestamp", formatDateTime(event.timestamp)],
    ["Source IP", orDash(event.source_ip)],
    ["Country", event.source_country ? `${flag(event.source_country_code)} ${event.source_country}` : "—"],
    ["City", orDash(event.source_city)],
    ["ASN", event.source_asn != null ? `AS${event.source_asn}` : "—"],
    ["Organization", orDash(event.source_organization)],
    ["Protocol", event.protocol ? event.protocol.toUpperCase() : "—"],
    ["Target port", orDash(event.destination_port)],
    ["Honeypot", orDash(event.honeypot)],
    ["Username", orDash(event.username)],
    ["Password", orDash(event.password)],
    ["Event type", eventTypeLabel(event.event_type)],
  ];

  return (
    <aside className="drawer" role="dialog" aria-label="Attack details" data-testid="attack-drawer">
      <div className="drawer-head">
        <div>
          <div className="drawer-kicker">Attack details</div>
          <div className="drawer-title">
            {eventTypeLabel(event.event_type)} · {event.source_country ?? "Unknown origin"}
          </div>
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close details">
          ✕
        </button>
      </div>

      <div className="drawer-risk">
        <div>
          <div className="stat-label">Risk rating</div>
          <SeverityBadge severity={event.severity} />
        </div>
        <div className="risk-meter" aria-label={`Risk score ${event.risk_score} of 100`}>
          <div className="risk-meter-fill" style={{ width: `${event.risk_score}%` }} />
        </div>
        <div className="risk-score mono">{event.risk_score}<span>/100</span></div>
      </div>

      <dl className="kv">
        {rows.map(([k, v]) => (
          <div key={k} className="kv-row">
            <dt>{k}</dt>
            <dd className="mono">{v}</dd>
          </div>
        ))}
        {event.command && (
          <div className="kv-row kv-block">
            <dt>Command</dt>
            <dd>
              <code>{event.command}</code>
            </dd>
          </div>
        )}
      </dl>

      <div className="drawer-section">
        <h3 className="panel-title">Why this rating</h3>
        {event.risk_factors.length === 0 ? (
          <p className="muted small">No risk rules matched — routine background noise.</p>
        ) : (
          <ul className="factors">
            {event.risk_factors.map((f) => (
              <li key={f.rule}>
                <span className="factor-points mono">+{f.points}</span>
                <span>{f.detail}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="muted small">Transparent rule-based score (not AI). Each matched rule adds fixed points, capped at 100.</p>
      </div>

      <div className="drawer-foot muted small">
        {publicMode ? "Public mode: IPs and passwords are masked; raw records withheld." : "Private mode: full telemetry shown."}{" "}
        Source: <span className="mono">{event.raw_source_type}</span> · ID <span className="mono">{event.id}</span>
      </div>
    </aside>
  );
}
