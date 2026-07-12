import { Badge } from "../common/Badge.jsx";
import { Card } from "../common/Card.jsx";
import { titleCase } from "../../utils/formatting.js";
import { optionValues } from "../../utils/report.js";
import { toneForLevel } from "../../utils/status.js";
import { FilterBar, SelectFilter, TextFilter } from "./FilterBar.jsx";

export function ActionsSection({ actions, filteredActions, filters, setFilters, resetFilters }) {
  const priorities = optionValues(actions, (action) => [action.priority]);
  const categories = optionValues(actions, (action) => [action.category]);

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
            <article className="report-item" key={action.id}>
              <span className="action-marker" aria-hidden="true" />
              <div className="item-heading">
                <Badge tone={toneForLevel(action.priority)}>{titleCase(action.priority)}</Badge>
                <Badge>{titleCase(action.category)}</Badge>
                <code>{action.rule_id}</code>
              </div>
              <h3>{action.title}</h3>
              <p>{action.description}</p>
              {action.affected_files?.length > 0 && <small>Affected: <span className="path-chip-list">{action.affected_files.map((file) => <code key={file}>{file}</code>)}</span></small>}
              <SmallList title="Related signals" items={action.related_signal_ids ?? []} />
              <SmallList title="Related readiness rules" items={action.related_readiness_rule_ids ?? []} />
              <SmallList title="Evidence" items={action.evidence ?? []} />
              <SmallList title="Limitations" items={action.limitations ?? []} />
            </article>
          ))}
        </div>
      )}
    </Card>
  );
}

function SmallList({ title, items }) {
  if (!items.length) return null;
  return <div className="mini-list"><strong>{title}</strong><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></div>;
}
