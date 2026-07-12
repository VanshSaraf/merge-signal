import { Badge } from "../common/Badge.jsx";
import { titleCase } from "../../utils/formatting.js";
import { toneForLevel } from "../../utils/status.js";

export function AssessmentRail({ snapshot }) {
  const items = assessmentItems(snapshot);

  return (
    <aside className="assessment-rail" aria-label="Assessment summary">
      <div className="rail-heading">
        <p className="eyebrow">Assessment</p>
        <h2>Merge signal</h2>
      </div>
      {items.map((item) => (
        <article className="rail-metric" key={item.label}>
          <div>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
          <Badge tone={item.tone}>{item.detail}</Badge>
          {item.meter != null && (
            <div className="rail-meter" aria-label={`${item.label} ${item.meter} of 100`}>
              <span style={{ width: `${Math.min(100, Math.max(0, item.meter))}%` }} />
            </div>
          )}
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

function toneForConfidence(level) {
  return { high: "success", medium: "warning", low: "danger" }[level] ?? "neutral";
}
