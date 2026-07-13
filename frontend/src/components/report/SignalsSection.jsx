import { useState } from "react";

import { Badge } from "../common/Badge.jsx";
import { Card } from "../common/Card.jsx";
import { titleCase } from "../../utils/formatting.js";
import { cleanEvidence, extractSafeUrl, optionValues } from "../../utils/report.js";
import { toneForLevel } from "../../utils/status.js";
import { FilterBar, SelectFilter, TextFilter } from "./FilterBar.jsx";

export function SignalsSection({ signals, filteredSignals, filters, setFilters, resetFilters }) {
  const severities = optionValues(signals, (signal) => [signal.severity]);
  const categories = optionValues(signals, (signal) => [signal.category]);
  const [expandedSignalId, setExpandedSignalId] = useState(null);

  return (
    <Card title="Review signals" eyebrow={`${filteredSignals.length} of ${signals.length}`}>
      <FilterBar onClear={resetFilters}>
        <SelectFilter id="signal-severity" label="Severity" value={filters.severity} onChange={(severity) => setFilters({ ...filters, severity })} options={severities} />
        <SelectFilter id="signal-category" label="Category" value={filters.category} onChange={(category) => setFilters({ ...filters, category })} options={categories} />
        <TextFilter id="signal-file" label="Affected file" value={filters.fileQuery} onChange={(fileQuery) => setFilters({ ...filters, fileQuery })} placeholder="path fragment" />
      </FilterBar>

      {filteredSignals.length === 0 ? <p className="empty-result">No signals match the current filters.</p> : (
        <div className="stack-list report-list signal-list">
          {filteredSignals.map((signal) => (
            <SignalRow
              expanded={expandedSignalId === signal.id}
              key={signal.id}
              onToggle={() => setExpandedSignalId(expandedSignalId === signal.id ? null : signal.id)}
              signal={signal}
            />
          ))}
        </div>
      )}
    </Card>
  );
}

function SignalRow({ signal, expanded, onToggle }) {
  return (
    <article className="report-item">
      <div className="item-heading">
        <Badge tone={toneForLevel(signal.severity)}>{titleCase(signal.severity)}</Badge>
        <Badge>{titleCase(signal.category)}</Badge>
        <span>{signal.affected_files?.length ?? 0} affected {(signal.affected_files?.length ?? 0) === 1 ? "file" : "files"}</span>
      </div>
      <h3>{signal.title}</h3>
      <p>{signal.description}</p>
      {signal.affected_files?.length > 0 && <small>Affected: <span className="path-chip-list">{signal.affected_files.map((file) => <code key={file}>{file}</code>)}</span></small>}
      <button className="button-link action-details-toggle" type="button" onClick={onToggle} aria-expanded={expanded}>
        {expanded ? "Hide technical details" : "Technical details"}
      </button>
      {expanded && (
        <div className="technical-details">
          <EvidenceList evidence={cleanEvidence(signal.evidence)} />
          <DisclosureList title="Limitations" items={signal.limitations ?? []} />
          <div className="mini-list">
            <strong>Technical rule ID</strong>
            <code>{signal.rule_id}</code>
          </div>
        </div>
      )}
    </article>
  );
}

function EvidenceList({ evidence }) {
  if (!evidence.length) return null;
  return <DisclosureList title="Evidence" items={evidence.map((item) => [item.kind, item.file, item.message].filter(Boolean).join(" · "))} />;
}

function DisclosureList({ title, items }) {
  if (!items.length) return null;
  return (
    <div className="mini-list">
      <strong>{title}</strong>
      <ul>{items.map((item) => <li key={item}><EvidenceText text={item} /></li>)}</ul>
    </div>
  );
}

function EvidenceText({ text }) {
  const url = extractSafeUrl(text);
  if (!url) return text;
  const [before] = String(text).split(url);
  return (
    <>
      {before.replace(/Details URL:\s*$/, "Details: ")}
      <a href={url} target="_blank" rel="noreferrer">Open details</a>
    </>
  );
}
