import { Badge } from "../common/Badge.jsx";
import { Card } from "../common/Card.jsx";
import { compactList, formatNumber, titleCase, uniqueLimit } from "../../utils/formatting.js";
import { toneForLevel } from "../../utils/status.js";

export function AnalysisDashboard({ snapshot }) {
  const limitations = uniqueLimit([
    ...(snapshot.merge_readiness?.limitations ?? []),
    ...(snapshot.merge_risk?.limitations ?? []),
    ...(snapshot.evidence_confidence?.limitations ?? []),
    ...(snapshot.completeness?.warnings ?? []),
  ], 6);
  const importantSignals = [...(snapshot.signals ?? [])]
    .sort((a, b) => severityOrder(a.severity) - severityOrder(b.severity) || a.rule_id.localeCompare(b.rule_id))
    .filter((signal) => ["high", "medium"].includes(signal.severity))
    .slice(0, 5);

  return (
    <div className="dashboard" aria-live="polite">
      <RepositoryHeader snapshot={snapshot} />
      <AssessmentRow snapshot={snapshot} />
      <MetricGrid snapshot={snapshot} />
      <div className="preview-grid">
        <HighestPriorityFiles files={(snapshot.ranked_files ?? []).slice(0, 5)} />
        <ReviewActions actions={(snapshot.review_actions ?? []).slice(0, 4)} />
        <ImportantSignals signals={importantSignals} />
        <Limitations limitations={limitations} />
      </div>
    </div>
  );
}

function RepositoryHeader({ snapshot }) {
  const metadata = snapshot.metadata;
  const reference = snapshot.reference;

  return (
    <Card className="repo-card">
      <div className="repo-header">
        <div>
          <p className="eyebrow">Repository</p>
          <h2>{reference.owner}/{reference.repository} <span>#{reference.pull_number}</span></h2>
          <p>{metadata.title}</p>
        </div>
        <a className="button button--secondary" href={reference.canonical_url} target="_blank" rel="noreferrer">
          Open on GitHub
        </a>
      </div>
      <dl className="repo-meta">
        <div><dt>Author</dt><dd>{metadata.author?.login ?? "Unknown"}</dd></div>
        <div><dt>Branch</dt><dd>{metadata.head_branch?.ref} → {metadata.base_branch?.ref}</dd></div>
        <div><dt>State</dt><dd>{metadata.draft ? "Draft" : titleCase(metadata.state)}</dd></div>
      </dl>
    </Card>
  );
}

function AssessmentRow({ snapshot }) {
  return (
    <section className="assessment-row" aria-label="Primary assessment">
      <AssessmentTile label="Readiness" value={titleCase(snapshot.merge_readiness?.decision)} tone={toneForLevel(snapshot.merge_readiness?.decision)} detail={snapshot.merge_readiness?.decisive_rule_id} />
      <AssessmentTile label="Merge risk" value={`${snapshot.merge_risk?.score ?? 0}/100`} tone={toneForLevel(snapshot.merge_risk?.level)} detail={titleCase(snapshot.merge_risk?.level)} />
      <AssessmentTile label="Evidence confidence" value={`${snapshot.evidence_confidence?.score ?? 0}/100`} tone={toneForConfidence(snapshot.evidence_confidence?.level)} detail={titleCase(snapshot.evidence_confidence?.level)} />
      <AssessmentTile label="CI" value={titleCase(snapshot.ci?.state)} tone={toneForLevel(snapshot.ci?.state)} detail={`Visibility: ${titleCase(snapshot.ci?.visibility)}`} />
    </section>
  );
}

function AssessmentTile({ label, value, tone, detail }) {
  return (
    <article className="assessment-tile">
      <span>{label}</span>
      <strong>{value}</strong>
      <Badge tone={tone}>{detail}</Badge>
    </article>
  );
}

function MetricGrid({ snapshot }) {
  const metrics = [
    ["Changed files", snapshot.metadata?.changed_files],
    ["Additions", snapshot.metadata?.additions],
    ["Deletions", snapshot.metadata?.deletions],
    ["Commits", snapshot.metadata?.commit_count],
    ["Review signals", snapshot.signal_summary?.total_signals],
    ["Review actions", snapshot.review_action_summary?.total_actions],
  ];

  return (
    <section className="metric-grid" aria-label="Snapshot metrics">
      {metrics.map(([label, value]) => (
        <div className="metric" key={label}>
          <span>{label}</span>
          <strong>{formatNumber(value)}</strong>
        </div>
      ))}
    </section>
  );
}

function HighestPriorityFiles({ files }) {
  return (
    <Card title="Highest-priority files" eyebrow="Top 5">
      <div className="file-list">
        {files.map((file) => (
          <article className="file-row" key={file.path}>
            <span className="rank">#{file.rank}</span>
            <div>
              <strong>{file.path}</strong>
              <p>{titleCase(file.primary_kind)} · {formatNumber(file.changes)} changed lines</p>
            </div>
            <Badge tone={toneForLevel(file.level)}>{file.score} · {titleCase(file.level)}</Badge>
          </article>
        ))}
      </div>
    </Card>
  );
}

function ReviewActions({ actions }) {
  return (
    <Card title="Review actions" eyebrow="Next checks">
      <div className="stack-list">
        {actions.map((action) => (
          <article className="list-item" key={action.id}>
            <Badge tone={toneForLevel(action.priority)}>{titleCase(action.priority)}</Badge>
            <div>
              <strong>{action.title}</strong>
              <p>{action.description}</p>
              {action.affected_files?.length > 0 && <small>{compactList(action.affected_files, 2)}</small>}
            </div>
          </article>
        ))}
      </div>
    </Card>
  );
}

function ImportantSignals({ signals }) {
  return (
    <Card title="Important signals" eyebrow="High and medium">
      <div className="stack-list">
        {signals.map((signal) => (
          <article className="list-item" key={signal.id}>
            <Badge tone={toneForLevel(signal.severity)}>{titleCase(signal.severity)}</Badge>
            <div>
              <strong>{signal.title}</strong>
              <p>{signal.description}</p>
              {signal.affected_files?.length > 0 && <small>{compactList(signal.affected_files, 2)}</small>}
            </div>
          </article>
        ))}
        {signals.length === 0 && <p className="muted">No high or medium review signals were observed.</p>}
      </div>
    </Card>
  );
}

function Limitations({ limitations }) {
  return (
    <Card title="Analysis limitations" eyebrow="Scope">
      <ul className="limitation-list">
        {limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
      </ul>
    </Card>
  );
}

function severityOrder(severity) {
  return { high: 0, medium: 1, low: 2, info: 3 }[severity] ?? 4;
}

function toneForConfidence(level) {
  return { high: "success", medium: "warning", low: "danger" }[level] ?? "neutral";
}
