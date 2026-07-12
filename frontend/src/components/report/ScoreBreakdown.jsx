import { formatNumber, titleCase } from "../../utils/formatting.js";

export function ScoreBreakdown({ title, items, valueKey = "applied_points", maxKey = "cap", nameKey = "group" }) {
  return (
    <div className="breakdown">
      <h3>{title}</h3>
      {(items ?? []).map((item) => {
        const value = item[valueKey] ?? item.awarded_points ?? 0;
        const max = item[maxKey] ?? item.maximum_points ?? 100;
        const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
        return (
          <div className="breakdown-row" key={item[nameKey] ?? item.id}>
            <div>
              <strong>{titleCase(item[nameKey] ?? item.name ?? item.id)}</strong>
              {item.status && <span>{titleCase(item.status)}</span>}
            </div>
            <div className="progress" aria-label={`${titleCase(item[nameKey] ?? item.id)} ${formatNumber(value)} of ${formatNumber(max)}`}>
              <span style={{ width: `${pct}%` }} />
            </div>
            <small>{formatNumber(value)} / {formatNumber(max)}</small>
          </div>
        );
      })}
    </div>
  );
}
