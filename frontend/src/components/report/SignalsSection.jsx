import { Badge } from "../common/Badge.jsx";
import { Card } from "../common/Card.jsx";
import { compactList, titleCase } from "../../utils/formatting.js";
import { cleanEvidence, optionValues } from "../../utils/report.js";
import { toneForLevel } from "../../utils/status.js";
import { FilterBar, SelectFilter, TextFilter } from "./FilterBar.jsx";

export function SignalsSection({ signals, filteredSignals, filters, setFilters, resetFilters }) {
  const severities = optionValues(signals, (signal) => [signal.severity]);
  const categories = optionValues(signals, (signal) => [signal.category]);

  return (
    <Card title="Review signals" eyebrow={`${filteredSignals.length} of ${signals.length}`}>
      <FilterBar onClear={resetFilters}>
        <SelectFilter id="signal-severity" label="Severity" value={filters.severity} onChange={(severity) => setFilters({ ...filters, severity })} options={severities} />
        <SelectFilter id="signal-category" label="Category" value={filters.category} onChange={(category) => setFilters({ ...filters, category })} options={categories} />
        <TextFilter id="signal-file" label="Affected file" value={filters.fileQuery} onChange={(fileQuery) => setFilters({ ...filters, fileQuery })} placeholder="path fragment" />
      </FilterBar>

      {filteredSignals.length === 0 ? <p className="empty-result">No signals match the current filters.</p> : (
        <div className="stack-list report-list">
          {filteredSignals.map((signal) => (
            <article className="report-item" key={signal.id}>
              <div className="item-heading">
                <Badge tone={toneForLevel(signal.severity)}>{titleCase(signal.severity)}</Badge>
                <Badge>{titleCase(signal.category)}</Badge>
                <code>{signal.rule_id}</code>
              </div>
              <h3>{signal.title}</h3>
              <p>{signal.description}</p>
              {signal.affected_files?.length > 0 && <small>Affected: {compactList(signal.affected_files, 4)}</small>}
              <EvidenceList evidence={cleanEvidence(signal.evidence)} />
              <SmallList title="Limitations" items={signal.limitations ?? []} />
            </article>
          ))}
        </div>
      )}
    </Card>
  );
}

function EvidenceList({ evidence }) {
  if (!evidence.length) return null;
  return <SmallList title="Evidence" items={evidence.map((item) => [item.kind, item.file, item.message].filter(Boolean).join(" · "))} />;
}

function SmallList({ title, items }) {
  if (!items.length) return null;
  return <div className="mini-list"><strong>{title}</strong><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></div>;
}
