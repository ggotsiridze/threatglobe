import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { SEVERITIES, type Timeline } from "../api/types";
import { SEVERITY_COLORS, formatNumber } from "../utils/format";

const KEYS = ["low", "medium", "high", "critical"] as const;

function hourLabel(iso: string) {
  return new Date(iso).toISOString().slice(11, 16);
}

interface TipProps {
  active?: boolean;
  label?: string;
  payload?: { dataKey: string; value: number }[];
}

function ChartTooltip({ active, label, payload }: TipProps) {
  if (!active || !payload?.length || !label) return null;
  const total = payload.reduce((sum, p) => sum + (p.value ?? 0), 0);
  return (
    <div className="chart-tip">
      <div className="chart-tip-title">
        {hourLabel(label)} UTC · <b className="mono">{formatNumber(total)}</b> events
      </div>
      {[...payload].reverse().map((p) => (
        <div key={p.dataKey} className="chart-tip-row">
          <span className="legend-swatch" style={{ background: SEVERITY_COLORS[p.dataKey.toUpperCase() as keyof typeof SEVERITY_COLORS] }} />
          <span>{p.dataKey.toUpperCase()}</span>
          <span className="mono">{formatNumber(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

export function TimelineChart({ timeline }: { timeline: Timeline | null }) {
  const data = timeline?.buckets ?? [];
  return (
    <section className="panel timeline" data-testid="timeline">
      <div className="panel-head">
        <h2 className="panel-title">
          Attack Volume Over Time
          {timeline && (
            <span className="panel-sub">
              {" "}
              · last {Math.round((timeline.buckets.length * timeline.bucket_minutes) / 60)}h, {timeline.bucket_minutes}-min buckets
            </span>
          )}
        </h2>
        <div className="legend" aria-label="Severity legend">
          {SEVERITIES.map((s) => (
            <span key={s} className="legend-item">
              <span className="legend-swatch" style={{ background: SEVERITY_COLORS[s] }} />
              {s}
            </span>
          ))}
        </div>
      </div>
      <div className="chart-box">
        {data.length === 0 ? (
          <div className="empty">Waiting for telemetry…</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#1a2436" vertical={false} />
              <XAxis dataKey="start" tickFormatter={hourLabel} stroke="#56637a" fontSize={11} tickLine={false} axisLine={false} minTickGap={28} />
              <YAxis stroke="#56637a" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} width={44} />
              <Tooltip content={<ChartTooltip />} cursor={{ stroke: "#8aa0c0", strokeWidth: 1, strokeDasharray: "3 3" }} />
              {KEYS.map((k) => {
                const color = SEVERITY_COLORS[k.toUpperCase() as keyof typeof SEVERITY_COLORS];
                return (
                  <Area
                    key={k}
                    type="monotone"
                    dataKey={k}
                    stackId="sev"
                    stroke={color}
                    strokeWidth={2}
                    fill={color}
                    fillOpacity={0.28}
                    isAnimationActive={false}
                    activeDot={{ r: 4, stroke: "#0d1422", strokeWidth: 2 }}
                  />
                );
              })}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
