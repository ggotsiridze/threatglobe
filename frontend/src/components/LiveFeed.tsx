import type { AttackEvent } from "../api/types";
import { eventTypeLabel, flag, formatTime, locationLabel, serviceLabel } from "../utils/format";
import { SeverityBadge } from "./SeverityBadge";

interface Props {
  events: AttackEvent[];
  title: string;
  selectedId: string | null;
  onSelect: (event: AttackEvent) => void;
}

export function LiveFeed({ events, title, selectedId, onSelect }: Props) {
  return (
    <section className="panel feed" data-testid="live-feed">
      <div className="panel-head">
        <h2 className="panel-title">{title}</h2>
        <span className="pulse" aria-hidden />
      </div>
      {events.length === 0 ? (
        <div className="empty">Waiting for events…</div>
      ) : (
        <ul className="feed-list">
          {events.slice(0, 60).map((e) => (
            <li key={e.id}>
              <button
                className={`feed-item${selectedId === e.id ? " selected" : ""}`}
                onClick={() => onSelect(e)}
                data-testid="feed-item"
                aria-label={`${e.severity} ${eventTypeLabel(e.event_type)} from ${locationLabel(e)}`}
              >
                <span className={`feed-bar sev-bg-${e.severity.toLowerCase()}`} aria-hidden />
                <span className="feed-main">
                  <span className="feed-top">
                    <span className="feed-flag" aria-hidden>{flag(e.source_country_code)}</span>
                    <span className="feed-loc">{locationLabel(e)}</span>
                    <span className="feed-time mono">{formatTime(e.timestamp)}</span>
                  </span>
                  <span className="feed-bottom">
                    <span className="feed-type">{eventTypeLabel(e.event_type)}</span>
                    <span className="feed-svc mono">{serviceLabel(e)}</span>
                    <span className="feed-hp">{e.honeypot}</span>
                    <SeverityBadge severity={e.severity} />
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
