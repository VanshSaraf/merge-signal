import { Badge } from "../common/Badge.jsx";
import { titleCase } from "../../utils/formatting.js";
import { toneForLevel } from "../../utils/status.js";

export function ReviewFocusPanel({ snapshot }) {
  const items = reviewFocusItems(snapshot);

  if (!items.length) {
    return null;
  }

  return (
    <aside className="review-focus-panel" aria-label="Review focus">
      <div className="rail-heading">
        <p className="eyebrow">Review focus</p>
        <h2>What to inspect first</h2>
      </div>
      {items.map((item) => (
        <article className="focus-item" key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          {item.detail && <p>{item.detail}</p>}
        </article>
      ))}
    </aside>
  );
}

export function AssessmentSummaryStrip({ snapshot }) {
  const [readiness, risk, confidence, ci] = assessmentItems(snapshot);

  return (
    <aside className="assessment-strip" aria-label="Compact assessment summary">
      <Badge tone={readiness.tone}>{readiness.value}</Badge>
      <span>Risk {snapshot.merge_risk?.score ?? 0}</span>
      <span>Confidence {snapshot.evidence_confidence?.score ?? 0}</span>
      <span>CI {ci.value}</span>
    </aside>
  );
}

function assessmentItems(snapshot) {
  return [
    {
      label: "Readiness",
      value: titleCase(snapshot.merge_readiness?.decision),
      detail: snapshot.merge_readiness?.decisive_rule_id,
      tone: toneForLevel(snapshot.merge_readiness?.decision),
    },
    {
      label: "Merge risk",
      value: `${snapshot.merge_risk?.score ?? 0}/100`,
      detail: titleCase(snapshot.merge_risk?.level),
      tone: toneForLevel(snapshot.merge_risk?.level),
      meter: snapshot.merge_risk?.score ?? 0,
    },
    {
      label: "Confidence",
      value: `${snapshot.evidence_confidence?.score ?? 0}/100`,
      detail: titleCase(snapshot.evidence_confidence?.level),
      tone: toneForConfidence(snapshot.evidence_confidence?.level),
      meter: snapshot.evidence_confidence?.score ?? 0,
    },
    {
      label: "CI",
      value: titleCase(snapshot.ci?.state),
      detail: `Visibility: ${titleCase(snapshot.ci?.visibility)}`,
      tone: toneForLevel(snapshot.ci?.state),
    },
  ];
}

function reviewFocusItems(snapshot) {
  const items = [];
  const primaryReason = snapshot.merge_readiness?.reasons?.[0];
  const topFile = snapshot.ranked_files?.[0];
  const firstAction = snapshot.review_actions?.[0];
  const confidence = snapshot.evidence_confidence;

  if (primaryReason?.title) {
    items.push({
      label: "Decisive reason",
      value: primaryReason.title,
      detail: primaryReason.explanation,
    });
  }

  if (topFile?.path) {
    items.push({
      label: "Highest-priority file",
      value: topFile.path,
      detail: `${titleCase(topFile.level)} priority · ${titleCase(topFile.primary_kind)}`,
    });
  }

  if (firstAction?.title) {
    items.push({
      label: "First reviewer action",
      value: firstAction.title,
      detail: firstAction.description,
    });
  }

  if (confidence && confidence.level !== "high") {
    items.push({
      label: "Evidence quality",
      value: `${confidence.score ?? 0}/100 · ${titleCase(confidence.level)}`,
      detail: "Evidence confidence is materially incomplete; read limitations before merging.",
    });
  }

  return items.slice(0, 4);
}

function toneForConfidence(level) {
  return { high: "success", medium: "warning", low: "danger" }[level] ?? "neutral";
}
