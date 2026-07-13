import { Badge } from "../common/Badge.jsx";
import { Card } from "../common/Card.jsx";
import { formatNumber, titleCase } from "../../utils/formatting.js";
import { toneForLevel } from "../../utils/status.js";
import { ScoreBreakdown } from "./ScoreBreakdown.jsx";

export function OverviewSection({ snapshot }) {
  return (
    <div className="report-section">
      <ReadinessStatement snapshot={snapshot} />
      <ReviewNext snapshot={snapshot} />
      <AssessmentRow snapshot={snapshot} />
      <MetricGrid snapshot={snapshot} />
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

function ReadinessStatement({ snapshot }) {
  const decision = titleCase(snapshot.merge_readiness?.decision);
  const primaryReason = snapshot.merge_readiness?.reasons?.[0];
  const reasonText = summarizeReason(primaryReason, snapshot);

  return (
    <section className="readiness-statement" aria-label="Readiness statement">
      <p className="eyebrow">Primary assessment</p>
      <h2>{decision}{reasonText ? ` because ${reasonText}.` : "."}</h2>
      {primaryReason?.explanation && <p>{primaryReason.explanation}</p>}
    </section>
  );
}

function summarizeReason(reason, snapshot) {
  if (!reason) return "";
  const ruleId = reason.rule_id ?? "";
  if (ruleId.includes("ci_failing") || snapshot.ci?.state === "failing") return "CI is failing";
  if (ruleId.includes("merge_conflict")) return "a merge conflict is reported";
  if (reason.title) return reason.title.replace(/\.$/, "").toLowerCase();
  return ruleId.replace(/^readiness\.[^.]+\./, "").replaceAll("_", " ");
}

function AssessmentRow({ snapshot }) {
  return (
    <section className="assessment-row" aria-label="Primary assessment">
      <AssessmentTile label="Readiness" value={titleCase(snapshot.merge_readiness?.decision)} tone={toneForLevel(snapshot.merge_readiness?.decision)} detail="Current verdict" />
      <AssessmentTile label="Merge risk" value={`${snapshot.merge_risk?.score ?? 0}/100`} tone={toneForLevel(snapshot.merge_risk?.level)} detail={titleCase(snapshot.merge_risk?.level)} meter={snapshot.merge_risk?.score ?? 0} />
      <AssessmentTile label="Evidence confidence" value={`${snapshot.evidence_confidence?.score ?? 0}/100`} tone={toneForConfidence(snapshot.evidence_confidence?.level)} detail={titleCase(snapshot.evidence_confidence?.level)} meter={snapshot.evidence_confidence?.score ?? 0} />
      <AssessmentTile label="CI" value={titleCase(snapshot.ci?.state)} tone={toneForLevel(snapshot.ci?.state)} detail={`Visibility: ${titleCase(snapshot.ci?.visibility)}`} />
    </section>
  );
}

function AssessmentTile({ label, value, tone, detail, meter }) {
  return (
    <article className="assessment-tile">
      <div className="assessment-tile__copy">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <Badge tone={tone}>{detail}</Badge>
      {meter != null && (
        <div className="assessment-meter" aria-label={`${label} ${meter} of 100`}>
          <span style={{ width: `${Math.min(100, Math.max(0, meter))}%` }} />
        </div>
      )}
    </article>
  );
}

function ReviewNext({ snapshot }) {
  const items = reviewNextItems(snapshot);

  if (!items.length) {
    return null;
  }

  return (
    <section className="review-next" aria-labelledby="review-next-heading">
      <div>
        <p className="eyebrow">Review next</p>
        <h2 id="review-next-heading">Start with the evidence that can change merge readiness.</h2>
      </div>
      <ol>
        {items.map((item) => (
          <li key={item.label}>
            <strong>{item.label}</strong>
            {item.detail && <span>{item.detail}</span>}
          </li>
        ))}
      </ol>
    </section>
  );
}

function reviewNextItems(snapshot) {
  const actions = (snapshot.review_actions ?? []).slice(0, 2).map((action) => ({
    label: action.title,
    detail: action.description,
  }));
  const topFile = snapshot.ranked_files?.[0];
  const fileItem = topFile?.path
    ? [{
        label: `Start with ${topFile.path}`,
        detail: `${titleCase(topFile.level)} priority changed file`,
      }]
    : [];

  return [...actions, ...fileItem].slice(0, 3);
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

function toneForConfidence(level) {
  return { high: "success", medium: "warning", low: "danger" }[level] ?? "neutral";
}
