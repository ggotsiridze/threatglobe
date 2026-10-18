import type { Stats } from "../api/types";
import { formatNumber } from "../utils/format";

export function StatCards({ stats }: { stats: Stats | null }) {
  const cards = [
    { id: "events", label: "Events Today", value: formatNumber(stats?.events_today), hint: `rolling ${stats?.window_hours ?? 24}h` },
    { id: "ips", label: "Unique Source IPs", value: formatNumber(stats?.unique_source_ips), hint: "distinct attackers" },
    { id: "countries", label: "Countries Observed", value: formatNumber(stats?.countries_observed), hint: "by GeoIP" },
    { id: "service", label: "Most Targeted Service", value: stats?.most_targeted_service ?? "—", hint: "by port" },
  ];
  return (
    <div className="stat-grid">
      {cards.map((c) => (
        <div className="stat-card" key={c.id} data-testid={`stat-${c.id}`}>
          <div className="stat-label">{c.label}</div>
          <div className="stat-value mono">{c.value}</div>
          <div className="stat-hint">{c.hint}</div>
        </div>
      ))}
    </div>
  );
}
