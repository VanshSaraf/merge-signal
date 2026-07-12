import { useState } from "react";

import { Badge } from "../common/Badge.jsx";
import { Card } from "../common/Card.jsx";
import { titleCase } from "../../utils/formatting.js";
import { optionValues } from "../../utils/report.js";
import { toneForLevel } from "../../utils/status.js";
import { FilterBar, SelectFilter, TextFilter } from "./FilterBar.jsx";

export function ActionsSection({ actions, filteredActions, filters, setFilters, resetFilters }) {
  const priorities = optionValues(actions, (action) => [action.priority]);
  const categories = optionValues(actions, (action) => [action.category]);
  const [expandedActionId, setExpandedActionId] = useState(null);

  return (
    <Card title="Review actions" eyebrow={`${filteredActions.length} of ${actions.length}`}>
      <p className="section-note">Actions are deterministic review prompts, not automated fixes or reviewer assignments.</p>
      <FilterBar onClear={resetFilters}>
        <SelectFilter id="action-priority" label="Priority" value={filters.priority} onChange={(priority) => setFilters({ ...filters, priority })} options={priorities} />
        <SelectFilter id="action-category" label="Category" value={filters.category} onChange={(category) => setFilters({ ...filters, category })} options={categories} />
        <TextFilter id="action-file" label="Affected file" value={filters.fileQuery} onChange={(fileQuery) => setFilters({ ...filters, fileQuery })} placeholder="path fragment" />
      </FilterBar>
      {filteredActions.length === 0 ? <p className="empty-result">No review actions match the current filters.</p> : (
        <div className="stack-list report-list action-list">
          {filteredActions.map((action) => (
            <ActionRow
              action={action}
              expanded={expandedActionId === action.id}
              key={action.id}
              onToggle={() => setExpandedActionId(expandedActionId === action.id ? null : action.id)}
            />
          ))}
        </div>
      )}
    </Card>
  );
}

function ActionRow({ action, expanded, onToggle }) {
  const affectedCount = action.affected_files?.length ?? 0;
  const signalCount = action.related_signal_ids?.length ?? 0;

  return (
    <article className="report-item" key={action.id}>
      <span className="action-marker" aria-hidden="true" />
      <div className="item-heading">
        <Badge tone={toneForLevel(action.priority)}>{titleCase(action.priority)}</Badge>
        <Badge>{titleCase(action.category)}</Badge>
        <span>{affectedCount} affected {affectedCount === 1 ? "file" : "files"}</span>
        <span>{signalCount} related {signalCount === 1 ? "signal" : "signals"}</span>
      </div>
      <h3>{action.title}</h3>
      <p>{action.description}</p>
      {action.affected_files?.length > 0 && <small>Affected: <span className="path-chip-list">{action.affected_files.map((file) => <code key={file}>{file}</code>)}</span></small>}
      <button className="button-link action-details-toggle" type="button" onClick={onToggle} aria-expanded={expanded}>
        {expanded ? "Hide details" : "View details"}
      </button>
      {expanded && (
        <div className="technical-details">
          <SmallList title="Evidence" items={action.evidence ?? []} />
          <SmallList title="Related signals" items={action.related_signal_ids ?? []} />
          <SmallList title="Related readiness rules" items={action.related_readiness_rule_ids ?? []} />
          <SmallList title="Limitations" items={action.limitations ?? []} />
          <div className="mini-list">
            <strong>Technical rule ID</strong>
            <code>{action.rule_id}</code>
          </div>
        </div>
      )}
    </article>
  );
}

function SmallList({ title, items }) {
  if (!items.length) return null;
  return <div className="mini-list"><strong>{title}</strong><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></div>;
}
