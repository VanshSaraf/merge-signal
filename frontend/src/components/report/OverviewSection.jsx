import { Badge } from "../common/Badge.jsx";
import { Card } from "../common/Card.jsx";
import { formatNumber, titleCase } from "../../utils/formatting.js";
import { toneForLevel } from "../../utils/status.js";
import { ScoreBreakdown } from "./ScoreBreakdown.jsx";

export function OverviewSection({ snapshot }) {
  return (
    <div className="report-section">
      <AssessmentRow snapshot={snapshot} />
      <MetricGrid snapshot={snapshot} />
      <KeyEvidence snapshot={snapshot} />
      <div className="breakdown-grid">
        <Card title="Merge-risk groups" eyebrow="Not a probability">
          <ScoreBreakdown title="Risk group breakdown" items={snapshot.merge_risk?.group_scores ?? []} />
        </Card>
        <Card title="Evidence confidence" eyebrow="Visibility">
          <ScoreBreakdown title="Confidence components" items={snapshot.evidence_confidence?.components ?? []} valueKey="awarded_points" maxKey="maximum_points" nameKey="name" />
        </Card>
      </div>
    </div>
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
      {metrics.map(([label, value]) => <div className="metric" key={label}><span>{label}</span><strong>{formatNumber(value)}</strong></div>)}
    </section>
  );
}

function KeyEvidence({ snapshot }) {
  const limitations = [
    ...(snapshot.merge_readiness?.limitations ?? []),
    ...(snapshot.merge_risk?.limitations ?? []),
    ...(snapshot.evidence_confidence?.limitations ?? []),
  ];

  return (
    <section className="overview-evidence" aria-label="Key evidence and limitations">
      <div>
        <p className="eyebrow">Decisive rule</p>
        <code>{snapshot.merge_readiness?.decisive_rule_id ?? "none"}</code>
      </div>
      <div>
        <p className="eyebrow">Key limitations</p>
        <p>{limitations.slice(0, 2).join(" ") || "No limitations returned for the current snapshot."}</p>
      </div>
    </section>
  );
}

function toneForConfidence(level) {
  return { high: "success", medium: "warning", low: "danger" }[level] ?? "neutral";
}
