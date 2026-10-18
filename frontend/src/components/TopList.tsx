import type { CountStat } from "../api/types";
import { flag, formatNumber } from "../utils/format";

interface Props {
  title: string;
  items: CountStat[] | undefined;
  withFlags?: boolean;
  testId?: string;
  limit?: number;
}

/** Ranked horizontal bars. Single series → one accent color, no legend. */
export function TopList({ title, items: all, withFlags, testId, limit = 8 }: Props) {
  const items = all?.slice(0, limit);
  const max = Math.max(1, ...(items ?? []).map((i) => i.count));
  return (
    <section className="panel" data-testid={testId}>
      <h2 className="panel-title">{title}</h2>
      {!items?.length ? (
        <div className="empty">No data yet</div>
      ) : (
        <ol className="toplist">
          {items.map((item) => (
            <li key={item.key} title={`${item.label}: ${formatNumber(item.count)} events`}>
              <div className="toplist-row">
                <span className="toplist-label">
                  {withFlags && <span className="flag" aria-hidden>{flag(item.key)}</span>}
                  {item.label}
                </span>
                <span className="toplist-count mono">{formatNumber(item.count)}</span>
              </div>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${(item.count / max) * 100}%` }} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
